import { Header } from "./components/Header";
import { FileInfoCard } from "./components/FileInfoCard";

import { AskSection } from "./components/AskSection";
import { ErrorState } from "./components/ErrorState";
import { LoadingState } from "./components/LoadingState";
import { EmptyState } from "./components/EmptyState";
import { useFileMetadata } from "./hooks/useFileMetadata";

function App() {
  const { metadata, loading, error, filePath } = useFileMetadata();

  return (
    <div className="w-full h-screen flex flex-col p-6 overflow-hidden">
      {/* 1. Header */}
      <Header />

      {/* 2. Main Content (Scrollable area) */}
      <main className="flex-1 overflow-y-auto mt-6 flex flex-col gap-6 pr-1">
        {loading ? (
          <LoadingState />
        ) : error ? (
          <ErrorState error={error} filePath={filePath} />
        ) : metadata ? (
          <>
            <FileInfoCard metadata={metadata} />
            <AskSection />
          </>
        ) : (
          <EmptyState />
        )}
      </main>
    </div>
  );
}

export default App;
