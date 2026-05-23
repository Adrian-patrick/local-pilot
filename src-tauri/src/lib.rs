use std::fs;
use std::path::Path;
use chrono::{DateTime, Local};

#[derive(serde::Serialize)]
struct FileMetadata {
    file_name: String,
    full_path: String,
    extension: String,
    file_size: u64,
    last_modified: String,
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

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![get_file_metadata, get_selected_file_path])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

