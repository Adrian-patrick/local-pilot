use std::fs;
use std::path::Path;
use std::io::Read;
use chrono::{DateTime, Local};

#[derive(serde::Serialize)]
struct FileMetadata {
    file_name: String,
    full_path: String,
    extension: String,
    file_size: u64,
    last_modified: String,
    is_dir: bool,
}

#[derive(serde::Deserialize)]
struct OllamaModel {
    name: String,
}

#[derive(serde::Deserialize)]
struct OllamaTagsResponse {
    models: Vec<OllamaModel>,
}

#[derive(serde::Serialize)]
struct OllamaGenerateRequest {
    model: String,
    prompt: String,
    stream: bool,
}

#[derive(serde::Deserialize)]
struct OllamaGenerateResponse {
    response: String,
}

#[tauri::command]
fn get_file_metadata(file_path: String) -> Result<FileMetadata, String> {
    let path = Path::new(&file_path);
    if !path.exists() {
        return Err(format!("Path does not exist: {}", file_path));
    }

    let metadata = fs::metadata(path)
        .map_err(|e| format!("Failed to read metadata: {}", e))?;

    let is_dir = path.is_dir();

    let file_name = path
        .file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("")
        .to_string();

    let full_path = path
        .canonicalize()
        .map(|p| p.to_string_lossy().to_string())
        .map(|s| s.strip_prefix(r"\\?\").unwrap_or(&s).to_string())
        .unwrap_or_else(|_| path.to_string_lossy().to_string());

    let extension = if is_dir {
        "FOLDER".to_string()
    } else {
        path.extension()
            .and_then(|e| e.to_str())
            .unwrap_or("")
            .to_uppercase()
    };

    let file_size = if is_dir { 0 } else { metadata.len() };

    let last_modified = metadata
        .modified()
        .ok()
        .and_then(|t| {
            let datetime: DateTime<Local> = t.into();
            Some(datetime.format("%Y-%m-%d %H:%M:%S").to_string())
        })
        .unwrap_or_else(|| "Unknown".to_string());

    Ok(FileMetadata {
        file_name,
        full_path,
        extension,
        file_size,
        last_modified,
        is_dir,
    })
}

#[tauri::command]
fn get_selected_file_path() -> Option<String> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() > 1 {
        // Skip executable, and skip any dev arguments starting with '-'
        for arg in args.iter().skip(1) {
            if !arg.starts_with('-') {
                return Some(arg.clone());
            }
        }
    }
    None
}

fn build_dir_tree(dir: &Path, depth: usize, max_depth: usize, count: &mut usize, max_items: usize) -> String {
    if depth > max_depth || *count >= max_items {
        return String::new();
    }
    let mut tree = String::new();
    let indent = "  ".repeat(depth);
    
    if let Ok(entries) = fs::read_dir(dir) {
        for entry in entries.flatten() {
            if *count >= max_items {
                tree.push_str(&format!("{}... (tree truncated, max {} items reached)\n", indent, max_items));
                break;
            }
            *count += 1;
            let name = entry.file_name().to_string_lossy().to_string();
            let is_dir = entry.path().is_dir();
            if is_dir {
                tree.push_str(&format!("{}- {}/\n", indent, name));
                tree.push_str(&build_dir_tree(&entry.path(), depth + 1, max_depth, count, max_items));
            } else {
                tree.push_str(&format!("{}- {}\n", indent, name));
            }
        }
    }
    tree
}

fn extract_docx(path: &Path) -> Result<String, String> {
    let file = fs::File::open(path).map_err(|e| e.to_string())?;
    let mut archive = zip::ZipArchive::new(file).map_err(|e| e.to_string())?;
    let mut doc_xml = archive.by_name("word/document.xml").map_err(|e| e.to_string())?;
    let mut xml_content = String::new();
    doc_xml.read_to_string(&mut xml_content).map_err(|e| e.to_string())?;
    
    // Strip XML tags to get raw text
    let mut text = String::new();
    let mut in_tag = false;
    for c in xml_content.chars() {
        if c == '<' {
            in_tag = true;
        } else if c == '>' {
            in_tag = false;
            text.push(' ');
        } else if !in_tag {
            text.push(c);
        }
    }
    let clean_text = text.split_whitespace().collect::<Vec<_>>().join(" ");
    Ok(clean_text)
}

fn extract_printable_strings(bytes: &[u8]) -> String {
    let mut result = String::new();
    let mut current_string = String::new();
    
    for &b in bytes {
        if b >= 32 && b <= 126 {
            current_string.push(b as char);
        } else {
            if current_string.len() >= 4 {
                result.push_str(&current_string);
                result.push('\n');
            }
            current_string.clear();
        }
    }
    if current_string.len() >= 4 {
        result.push_str(&current_string);
    }
    result
}

#[tauri::command]
fn read_file_content(file_path: String) -> Result<String, String> {
    let path = Path::new(&file_path);
    if !path.exists() {
        return Err(format!("Path does not exist: {}", file_path));
    }

    if path.is_dir() {
        let mut count = 0;
        let tree = build_dir_tree(path, 0, 3, &mut count, 100);
        return Ok(format!("Directory Structure:\n{}", tree));
    }

    let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("").to_lowercase();
    
    if ext == "pdf" {
        return match pdf_extract::extract_text(path) {
            Ok(text) => Ok(text),
            Err(e) => Ok(format!("[Failed to parse PDF: {}]", e)),
        };
    }
    
    if ext == "docx" {
        return match extract_docx(path) {
            Ok(text) => Ok(text),
            Err(e) => Ok(format!("[Failed to parse DOCX: {}]", e)),
        };
    }

    let mut file = fs::File::open(path).map_err(|e| format!("Failed to open file: {}", e))?;
    let max_read = 100 * 1024; // 100 KB safe limit for generic files
    let mut buffer = vec![0; max_read + 1];
    let bytes_read = file.read(&mut buffer).map_err(|e| format!("Failed to read file: {}", e))?;

    if bytes_read == 0 {
        return Ok("".to_string());
    }

    let read_slice = &buffer[..bytes_read];

    match String::from_utf8(read_slice.to_vec()) {
        Ok(text) => {
            if bytes_read > max_read {
                let mut end = max_read;
                while !text.is_char_boundary(end) && end > 0 {
                    end -= 1;
                }
                Ok(format!(
                    "{}\n\n[WARNING: File contents truncated to 100KB to respect context limits]",
                    &text[..end]
                ))
            } else {
                Ok(text)
            }
        }
        Err(_) => {
            // Fallback to extracting printable ASCII strings from binary
            let strings = extract_printable_strings(read_slice);
            Ok(format!("[Binary file detected. Extracted readable strings:]\n{}", strings))
        }
    }
}

#[tauri::command]
fn get_ollama_models() -> Result<Vec<String>, String> {
    let client = reqwest::blocking::Client::new();
    let response = client.get("http://localhost:11434/api/tags")
        .timeout(std::time::Duration::from_secs(2))
        .send()
        .map_err(|e| format!("Ollama server is not running on http://localhost:11434. (Error: {})", e))?;

    if !response.status().is_success() {
        return Err(format!("Ollama server returned error: {}", response.status()));
    }

    let tags: OllamaTagsResponse = response.json()
        .map_err(|e| format!("Failed to parse Ollama models response: {}", e))?;

    let mut model_names: Vec<String> = tags.models.into_iter().map(|m| m.name).collect();
    model_names.sort();
    Ok(model_names)
}

#[tauri::command]
fn ask_ollama(model: String, prompt: String) -> Result<String, String> {
    let client = reqwest::blocking::Client::new();
    let request_payload = OllamaGenerateRequest {
        model,
        prompt,
        stream: false,
    };

    let response = client.post("http://localhost:11434/api/generate")
        .json(&request_payload)
        .timeout(std::time::Duration::from_secs(60)) // Give local LLM plenty of time to formulate an answer
        .send()
        .map_err(|e| format!("Failed to connect to Ollama: {}", e))?;

    if !response.status().is_success() {
        return Err(format!("Ollama returned an error status: {}", response.status()));
    }

    let gen_response: OllamaGenerateResponse = response.json()
        .map_err(|e| format!("Failed to parse Ollama response: {}", e))?;

    Ok(gen_response.response)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            get_file_metadata,
            get_selected_file_path,
            read_file_content,
            get_ollama_models,
            ask_ollama
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}


