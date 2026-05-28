import { useState, useEffect, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import { FileMetadata } from "../types/file";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export function AskSection({ metadata }: { metadata: FileMetadata | null }) {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [models, setModels] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [status, setStatus] = useState<"checking" | "connected" | "offline" | "no-models">("checking");
  const [submitting, setSubmitting] = useState(false);
  const [statusError, setStatusError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Check Ollama status and load models
  const checkOllama = async () => {
    try {
      setStatus("checking");
      setStatusError(null);
      const availableModels: string[] = await invoke("get_ollama_models");
      
      if (availableModels.length > 0) {
        setModels(availableModels);
        // Default to llama3 or llama2 or first model if not found
        const preferred = availableModels.find(
          m => m.toLowerCase().includes("llama3") || m.toLowerCase().includes("llama")
        ) || availableModels[0];
        setSelectedModel(preferred);
        setStatus("connected");
      } else {
        setStatus("no-models");
      }
    } catch (err) {
      console.error("Ollama connection check failed:", err);
      setStatus("offline");
      setStatusError(typeof err === "string" ? err : String(err));
    }
  };

  useEffect(() => {
    checkOllama();
  }, []);

  // Auto scroll to bottom of chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, submitting]);

  const handleSubmit = async (textToSend: string) => {
    if (!textToSend.trim() || status !== "connected" || submitting) return;

    const userText = textToSend.trim();
    setQuery("");
    setMessages(prev => [...prev, { role: "user", content: userText }]);
    setSubmitting(true);

    try {
      let fileContent = "";
      if (metadata) {
        try {
          fileContent = await invoke("read_file_content", { filePath: metadata.full_path });
        } catch (err) {
          console.error("Error reading file context:", err);
          fileContent = `[Could not read file context: ${err}]`;
        }
      }

      // Build structured prompt for local model
      let prompt = "";
      if (metadata) {
        prompt = `You are Local Pilot, an offline, highly intelligent software developer assistant.
You are helping the user with their loaded file.

---
FILE DETAILS:
Name: ${metadata.file_name}
Path: ${metadata.full_path}
Size: ${metadata.file_size} bytes
Last Modified: ${metadata.last_modified}
---
FILE CONTENTS:
${fileContent}
---

INSTRUCTIONS:
- Analyze the file contents and metadata provided above.
- Answer the user's question directly, clearly, and concisely.
- For code improvements or explanations, write premium clean code blocks with clear syntax.

USER QUERY:
${userText}`;
      } else {
        prompt = `You are Local Pilot, an offline, highly intelligent software developer assistant.
Please answer the user's question directly, clearly, and concisely.

USER QUERY:
${userText}`;
      }

      // Invoke Ollama via Rust backend to bypass CORS and guarantee sandboxing
      const response: string = await invoke("ask_ollama", {
        model: selectedModel,
        prompt: prompt,
      });

      setMessages(prev => [...prev, { role: "assistant", content: response }]);
    } catch (err) {
      console.error("Failed to generate response:", err);
      const errorMsg = typeof err === "string" ? err : String(err);
      setMessages(prev => [
        ...prev,
        {
          role: "assistant",
          content: `❌ **Failed to generate response from Ollama.**\n\nError: ${errorMsg}\n\nPlease verify Ollama is running and has the model "${selectedModel}" downloaded.`,
        },
      ]);
    } finally {
      setSubmitting(false);
    }
  };

  const samplePrompts = metadata
    ? [
        { label: "Summarize File", text: "Please write a concise technical summary of this file's contents, explaining its main purpose and structure." },
        { label: "Find Potential Bugs", text: "Look closely at this file and point out any potential bugs, safety issues, logical errors, or code smells." },
        { label: "Explain Code", text: "Can you provide a step-by-step technical explanation of what this file does?" },
      ]
    : [
        { label: "Write a Fast API Mock", text: "Write a simple FastAPI mock server in Python that returns standard dummy JSON values." },
        { label: "Learn about Ollama", text: "How does Ollama work under the hood? Explain its model management and endpoint system." },
        { label: "Explain Rust Memory Safety", text: "Briefly explain the concepts of ownership, borrowing, and lifetimes in Rust." },
      ];

  return (
    <div className="w-full bg-white/[0.02] border border-white/5 rounded-2xl p-6 backdrop-blur-md animate-fade-in flex flex-col gap-4 shadow-xl">
      {/* Header section with Model Selection & Status */}
      <div className="flex items-center justify-between border-b border-white/5 pb-4">
        <div>
          <h3 className="text-sm font-semibold text-white tracking-tight flex items-center gap-2">
            Ask Local Pilot
            <span className="text-[9px] font-bold px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 uppercase tracking-wider">
              Local LLM Active
            </span>
          </h3>
          <p className="text-xs text-zinc-400">
            {metadata ? `Query sandbox bound to "${metadata.file_name}"` : "General local LLM query playground"}
          </p>
        </div>

        {/* Ollama Status / Model Selector */}
        {status === "checking" && (
          <div className="flex items-center gap-2 text-xs text-zinc-400">
            <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
            Connecting Ollama...
          </div>
        )}

        {status === "connected" && (
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-zinc-400 font-bold uppercase tracking-wider">LLM Model:</span>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="bg-black/40 border border-white/10 rounded-lg px-2.5 py-1 text-xs text-white outline-none focus:border-indigo-500 transition cursor-pointer"
            >
              {models.map((m) => (
                <option key={m} value={m} className="bg-zinc-950 text-white">
                  {m}
                </option>
              ))}
            </select>
          </div>
        )}

        {status === "offline" && (
          <div className="flex items-center gap-1.5 text-xs text-rose-400 font-semibold px-2.5 py-1 rounded-full bg-rose-500/10 border border-rose-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse" />
            Offline
          </div>
        )}

        {status === "no-models" && (
          <div className="flex items-center gap-1.5 text-xs text-amber-400 font-semibold px-2.5 py-1 rounded-full bg-amber-500/10 border border-amber-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
            No Models
          </div>
        )}
      </div>

      {/* Main Conversation Log or Empty/Error States */}
      {status === "offline" ? (
        <div className="bg-black/20 border border-rose-500/15 rounded-xl p-5 flex flex-col gap-3 text-left">
          <div className="flex items-center gap-2 text-rose-400 font-semibold text-sm">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            Ollama Service Not Detected
          </div>
          <p className="text-xs text-zinc-400 leading-relaxed">
            Local Pilot connects to an Ollama server running locally on <code className="text-white bg-black/40 px-1 py-0.5 rounded">http://localhost:11434</code>. Please ensure Ollama is installed and running.
          </p>
          {statusError && (
            <div className="text-[10px] text-rose-300/80 font-mono bg-rose-950/20 border border-rose-500/10 p-2 rounded-lg break-all">
              Details: {statusError}
            </div>
          )}
          <div className="flex items-center gap-3 mt-1">
            <button
              onClick={checkOllama}
              className="px-4 py-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-rose-300 font-semibold text-xs transition active:scale-95"
            >
              Retry Connection
            </button>
            <a
              href="https://ollama.com"
              target="_blank"
              rel="noreferrer"
              className="text-xs text-indigo-400 hover:text-indigo-300 underline font-medium"
            >
              Download Ollama &rarr;
            </a>
          </div>
        </div>
      ) : status === "no-models" ? (
        <div className="bg-black/20 border border-amber-500/15 rounded-xl p-5 flex flex-col gap-3 text-left">
          <div className="flex items-center gap-2 text-amber-400 font-semibold text-sm">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            No Models Downloaded
          </div>
          <p className="text-xs text-zinc-400 leading-relaxed">
            Ollama is connected, but we couldn't find any downloaded models. You must pull an LLM model before asking questions.
          </p>
          <div className="bg-black/40 px-3 py-2 rounded-lg text-xs font-mono text-zinc-300 border border-white/5 select-all cursor-pointer">
            ollama run llama3
          </div>
          <div className="flex items-center gap-3 mt-1">
            <button
              onClick={checkOllama}
              className="px-4 py-1.5 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-300 font-semibold text-xs transition active:scale-95"
            >
              Refresh Models
            </button>
          </div>
        </div>
      ) : (
        /* Conversation container */
        <div className="flex flex-col gap-4">
          <div className="w-full max-h-[300px] overflow-y-auto pr-1 flex flex-col gap-3.5 scrollbar-thin scrollbar-thumb-zinc-800 scrollbar-track-transparent">
            {messages.length === 0 ? (
              <div className="py-4 text-center flex flex-col items-center gap-4">
                <p className="text-xs text-zinc-500 italic max-w-sm">
                  {metadata
                    ? `Ask questions about "${metadata.file_name}" or pick a suggestion below:`
                    : "No queries submitted yet. Ask anything to start talking to the local LLM!"}
                </p>
                <div className="flex flex-wrap justify-center gap-2 max-w-lg">
                  {samplePrompts.map((p) => (
                    <button
                      key={p.label}
                      onClick={() => handleSubmit(p.text)}
                      className="px-3 py-1.5 rounded-full bg-white/[0.03] hover:bg-white/[0.07] border border-white/5 text-[11px] font-medium text-zinc-300 transition duration-200 active:scale-95"
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <>
                {messages.map((m, idx) => (
                  <div
                    key={idx}
                    className={`flex flex-col max-w-[85%] rounded-2xl px-4 py-3 text-xs leading-relaxed transition-all duration-300 animate-fade-in ${
                      m.role === "user"
                        ? "bg-indigo-500/10 border border-indigo-500/20 text-indigo-100 self-end rounded-tr-sm"
                        : "bg-white/[0.03] border border-white/5 text-zinc-200 self-start rounded-tl-sm"
                    }`}
                  >
                    <div className="font-semibold text-[9px] uppercase tracking-wider text-zinc-400 mb-1">
                      {m.role === "user" ? "You" : `Local Pilot (${selectedModel})`}
                    </div>
                    <div className="whitespace-pre-wrap font-sans break-words selection:bg-indigo-500/30">
                      {m.content}
                    </div>
                  </div>
                ))}
                
                {submitting && (
                  <div className="bg-white/[0.03] border border-white/5 text-zinc-400 self-start rounded-2xl rounded-tl-sm px-4 py-3 text-xs max-w-[85%] flex items-center gap-2.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce [animation-delay:-0.3s]" />
                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce [animation-delay:-0.15s]" />
                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce" />
                    <span className="text-[10px] italic text-zinc-500">Generating local response...</span>
                  </div>
                )}
                
                <div ref={messagesEndRef} />
              </>
            )}
          </div>

          {/* Interactive bottom Input Area */}
          <div className="relative flex items-center gap-2 mt-1">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(query);
                }
              }}
              placeholder={
                metadata
                  ? `Ask about "${metadata.file_name}"...`
                  : "Ask the local LLM anything..."
              }
              disabled={submitting || status !== "connected"}
              className="w-full h-12 bg-black/40 border border-white/5 rounded-xl pl-4 pr-12 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/20 transition disabled:opacity-50 disabled:cursor-not-allowed"
            />

            <button
              onClick={() => handleSubmit(query)}
              disabled={!query.trim() || submitting || status !== "connected"}
              className={`absolute right-2 flex items-center justify-center w-8 h-8 rounded-lg transition-all duration-300 ${
                query.trim() && !submitting && status === "connected"
                  ? "bg-indigo-500 hover:bg-indigo-600 text-white cursor-pointer active:scale-95"
                  : "bg-zinc-800/80 text-zinc-600 cursor-not-allowed"
              }`}
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </button>
          </div>

          {metadata && messages.length > 0 && (
            <div className="text-[10px] text-zinc-500 flex items-center gap-1.5 px-1">
              <svg className="w-3.5 h-3.5 text-indigo-400/50" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
              Every response is generated completely offline and secured locally on your system.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
