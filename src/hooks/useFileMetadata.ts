import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { FileMetadata } from "../types/file";

export function useFileMetadata() {
  const [metadata, setMetadata] = useState<FileMetadata | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [filePath, setFilePath] = useState<string | null>(null);

  useEffect(() => {
    async function init() {
      try {
        setLoading(true);
        setError(null);
        
        // 1. Get selected file path from CLI arguments
        const path: string | null = await invoke("get_selected_file_path");
        setFilePath(path);

        if (path) {
          // 2. Fetch metadata for the selected file
          const data: FileMetadata = await invoke("get_file_metadata", { filePath: path });
          setMetadata(data);
        } else {
          // No file selected (e.g. opened directly)
          setMetadata(null);
        }
      } catch (err) {
        console.error("Error loading file metadata:", err);
        setError(typeof err === "string" ? err : String(err));
      } finally {
        setLoading(false);
      }
    }

    init();
  }, []);

  return { metadata, loading, error, filePath };
}
