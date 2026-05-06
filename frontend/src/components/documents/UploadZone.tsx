import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { useQueryClient } from "@tanstack/react-query";
import { Upload } from "lucide-react";
import toast from "react-hot-toast";

import { api } from "../../lib/axios";

const DOC_TYPES = [
  "FIR",
  "AFFIDAVIT",
  "WITNESS_STATEMENT",
  "BAIL_APPLICATION",
  "LEGAL_NOTICE",
  "OTHER"
];

export function UploadZone({ sessionId }: { sessionId: string }) {
  const queryClient = useQueryClient();
  const [uploading, setUploading] = useState(false);
  const [docType, setDocType] = useState("FIR");

  const onDrop = useCallback(
    async (files: File[]) => {
      for (const file of files) {
        setUploading(true);
        const form = new FormData();
        form.append("file", file);
        form.append("title", file.name.replace(/\.[^.]+$/, ""));
        form.append("document_type", docType);
        form.append("session_id", sessionId);
        try {
          await api.post("/documents/upload/", form, {
            headers: { "Content-Type": "multipart/form-data" }
          });
          toast.success(`${file.name} uploaded`);
          queryClient.invalidateQueries({ queryKey: ["documents", sessionId] });
        } catch {
          return;
        } finally {
          setUploading(false);
        }
      }
    },
    [docType, queryClient, sessionId]
  );

  const { getInputProps, getRootProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"], "image/*": [".png", ".jpg", ".jpeg"] },
    disabled: uploading
  });

  return (
    <div className="space-y-3">
      <select
        value={docType}
        onChange={(event) => setDocType(event.target.value)}
        className="bg-surface-700 border border-surface-600 text-gray-300 rounded-lg px-3 py-2 text-sm w-full"
      >
        {DOC_TYPES.map((type) => (
          <option key={type}>{type}</option>
        ))}
      </select>
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors ${
          isDragActive
            ? "border-accent bg-accent/5"
            : "border-surface-600 hover:border-accent/50"
        }`}
      >
        <input {...getInputProps()} />
        <Upload className="mx-auto mb-3 text-gray-500" size={32} />
        <p className="text-gray-400 text-sm">
          {uploading ? "Uploading..." : "Drop PDFs or images here, or click to browse"}
        </p>
      </div>
    </div>
  );
}
