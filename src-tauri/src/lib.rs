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
        return Err(format!("File does not exist: {}", file_path));
    }
    if !path.is_file() {
        return Err(format!("Path is not a file: {}", file_path));
    }

    let metadata = fs::metadata(path)
        .map_err(|e| format!("Failed to read metadata: {}", e))?;

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

    let extension = path
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or("")
        .to_uppercase();

    let file_size = metadata.len();

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

#[tauri::command]
fn read_file_content(file_path: String) -> Result<String, String> {
    let path = Path::new(&file_path);
    if !path.exists() {
        return Err(format!("File does not exist: {}", file_path));
    }
    if !path.is_file() {
        return Err(format!("Path is not a file: {}", file_path));
    }

    let mut file = fs::File::open(path).map_err(|e| format!("Failed to open file: {}", e))?;
    let max_read = 50 * 1024; // 50 KB safe limit
    let mut buffer = vec![0; max_read + 1];
    let bytes_read = file.read(&mut buffer).map_err(|e| format!("Failed to read file: {}", e))?;

    if bytes_read == 0 {
        return Ok("".to_string());
    }

    let read_slice = &buffer[..bytes_read];

    match String::from_utf8(read_slice.to_vec()) {
        Ok(text) => {
            if bytes_read > max_read {
                // Safely find the UTF-8 boundary to avoid panic on slicing
                let mut end = max_read;
                while !text.is_char_boundary(end) && end > 0 {
                    end -= 1;
                }
                Ok(format!(
                    "{}\n\n[WARNING: File contents truncated to 50KB to respect context limits]",
                    &text[..end]
                ))
            } else {
                Ok(text)
            }
        }
        Err(_) => {
            // Keep app premium and safe by bypassing non-UTF-8 binary data
            Ok("[Binary file: unable to read text contents]".to_string())
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


