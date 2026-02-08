import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Upload } from "lucide-react";

export function DatasetUpload() {
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setMessage("");

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch("/api/upload/dataset", {
        method: "POST",
        body: formData,
      });

      if (response.ok) {
        setMessage(`✅ Dataset "${file.name}" erfolgreich hochgeladen! Seite wird neu geladen...`);
        setTimeout(() => window.location.reload(), 2000);
      } else {
        const error = await response.json();
        setMessage(`❌ Fehler: ${error.detail || "Upload fehlgeschlagen"}`);
      }
    } catch (error) {
      setMessage(`❌ Fehler beim Upload: ${error}`);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="flex items-center gap-4">
      <label
        htmlFor="dataset-upload"
        className="flex items-center gap-2 px-4 py-2 rounded-lg border border-border/50 bg-background/50 hover:bg-accent/50 cursor-pointer transition-colors"
      >
        <Upload className="w-4 h-4" />
        <span className="text-sm">
          {uploading ? "Uploading..." : "Eigenes Dataset testen"}
        </span>
      </label>
      <input
        id="dataset-upload"
        type="file"
        accept=".csv"
        onChange={handleFileUpload}
        disabled={uploading}
        className="hidden"
      />
      {message && (
        <span className="text-xs text-muted-foreground">{message}</span>
      )}
    </div>
  );
}
