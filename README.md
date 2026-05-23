# Local Pilot — Stage 1 Prototype

A modern, native, contextual workspace desktop application. 
The Stage 1 prototype validates OS-native context injection: right-clicking any file inside Windows Explorer, choosing **"Ask Local Pilot"**, and launching the desktop app with the selected file's metadata parsed and displayed instantly in a premium dark glassmorphic UI.

---

## 🚀 Primary Success Flow

```
Right-Click File ──> Ask Local Pilot ──> Opens App ──> Selected File Context Displayed
```

---

## 🛠️ Tech Stack

- **Desktop Framework**: [Tauri v2](https://tauri.app) (Rust Backend)
- **Frontend**: [React 19](https://react.dev), [TypeScript](https://www.typescriptlang.org)
- **Styling**: [TailwindCSS v4](https://tailwindcss.com) (Utility-first, dark theme)
- **Python Environment (For future stages)**: [uv](https://github.com/astral-sh/uv) (FastAPI, Uvicorn, Pydantic)

---

## 📂 Folder Structure

```text
local-pilot/
│
├── .venv/                      # Python Virtual Environment (uv managed)
├── src-tauri/                  # Tauri Rust backend, configuration, and dependencies
│   ├── src/
│   │   ├── lib.rs              # Rust entrypoint, Tauri commands, and metadata parsing
│   │   └── main.rs             # Application runner
│   └── Cargo.toml              # Rust crate manifest
│
├── src/                        # React Frontend
│   ├── assets/                 # SVGs and static media assets
│   ├── components/             # Reusable UI components
│   │   ├── Header.tsx          # Workspace window header
│   │   ├── FileInfoCard.tsx    # Context card displaying parsed file metadata
│   │   ├── AskSection.tsx      # Disabled visual-only prompt sandbox
│   │   ├── ErrorState.tsx      # Graceful invalid file/permission error UI
│   │   ├── EmptyState.tsx      # Direct launch guide when opened without file context
│   │   └── LoadingState.tsx    # Skeleton screen loading indicator
│   ├── hooks/
│   │   └── useFileMetadata.ts  # State management hook for backend communication
│   ├── types/
│   │   └── file.ts             # TypeScript definitions matching Rust structs
│   ├── App.tsx                 # Main layout coordinator
│   └── index.css               # TailwindCSS v4 imports & custom styles
│
├── scripts/                    # Context Menu integration scripts
│   ├── register-context-menu.ps1    # PowerShell context menu register script
│   ├── unregister-context-menu.ps1  # PowerShell context menu cleanup script
│   └── register-context-menu.reg    # Static registry import backup file
│
├── package.json                # Frontend package dependencies & NPM scripts
└── README.md                   # Project documentation
```

---

## ⚙️ Environment Setup & Running Locally

### Prerequisites
1. **Node.js**: v20 or later
2. **Rust**: Stable toolchain (rustup)
3. **Python**: `uv` installed (`pip install uv`)

### 1. Python Environment Setup (Mandatory)
We use `uv` for python dependencies management. The virtual environment is created and standard packages are pre-loaded:
```bash
# Verify venv & install dependencies
uv sync
```

### 2. Frontend & Tauri Project Setup
Install node dependencies:
```bash
npm install
```

### 3. Run in Development Mode
Launch the live development server. You can run the app directly, or pass a custom file path argument to test context injection in development!
```bash
# Option A: Open directly (shows the helpful empty state guide)
npm run tauri dev

# Option B: Pass a mock file path to test context injection
npm run tauri dev -- -- "C:\path\to\your\file.txt"
```

### 4. Build for Release (Production)
Compile the standalone desktop application (`.exe` binary):
```bash
npm run tauri build
```
The compiled binary will be generated under:
`src-tauri/target/release/Local Pilot.exe`

---

## 🎛️ Windows Context Menu Integration

We integrate classically and safely at the user level (`HKCU`), requiring no administrator privileges!

### Automatic Registration (Recommended)
1. Build the release binary: `npm run tauri build`
2. Open PowerShell in the project directory and run the registration script:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\register-context-menu.ps1
   ```
3. Open Windows Explorer, right-click any file (or folder), and choose **"Ask Local Pilot"**! (Note: On Windows 11, it may appear in the *"Show more options"* classical context menu).

### Manual Registration
If you prefer manual import, we've created a registry file at `scripts/register-context-menu.reg` pre-populated with your exact workspace directory. Simply double-click the file to import the entries!

### Cleanup / Uninstallation
To cleanly remove all context menu entries from the Windows registry, run:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\unregister-context-menu.ps1
```

---

## 🧬 Argument Passing & Backend Mechanics

### 1. Registry Trigger
When you click **"Ask Local Pilot"** on a file, Windows executes the registered command:
```cmd
"C:\path\to\Local Pilot.exe" "%1"
```
where `%1` is substituted with the absolute file path of the right-clicked file.

### 2. Rust Arg Parsing
On startup, the Rust backend parses the system arguments, filters out internal Tauri/Vite flags starting with `-` (such as `--port`), and exposes the target path:
```rust
// src-tauri/src/lib.rs
#[tauri::command]
fn get_selected_file_path() -> Option<String> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() > 1 {
        for arg in args.iter().skip(1) {
            if !arg.starts_with('-') {
                return Some(arg.clone());
            }
        }
    }
    None
}
```

### 3. Metadata Extraction
Using the native Rust file system library (`std::fs`), we extract exact metadata (handling permission errors, missing files, and cleaning up Windows UNC file prefixes):
```rust
#[tauri::command]
fn get_file_metadata(file_path: String) -> Result<FileMetadata, String> {
    let path = Path::new(&file_path);
    // ... validation ...
    let metadata = fs::metadata(path)?;
    // ... extract filename, uppercase extension, size, last_modified ...
}
```

### 4. React Coordination
On mounting, the React application checks for a file argument via `useFileMetadata` hook, calls the Rust backend commands, and handles transitions (Loading -> Success Info Card OR Error State).
