"use client";

import { useState, useCallback } from "react";
import { useDropzone, FileRejection } from "react-dropzone";
import { apiClient, ApiError } from "@/lib/api-client";

interface UploadingFile {
  id: string;
  filename: string;
  progress: number;
  status: "uploading" | "done" | "error";
  error?: string;
}

interface DocumentUploadProps {
  onUploadComplete: () => void;
  documentCount: number;
  maxDocuments: number;
}

export function DocumentUpload({ onUploadComplete, documentCount, maxDocuments }: DocumentUploadProps) {
  const [uploadingFiles, setUploadingFiles] = useState<UploadingFile[]>([]);
  const remainingSlots = maxDocuments - documentCount;

  const onDrop = useCallback(async (acceptedFiles: File[], rejectedFiles: FileRejection[]) => {
    // Handle rejections
    if (rejectedFiles.length > 0) {
      rejectedFiles.forEach(rejection => {
        const error = rejection.errors[0]?.message || "Invalid file";
        setUploadingFiles(prev => [...prev, {
          id: crypto.randomUUID(),
          filename: rejection.file.name,
          progress: 0,
          status: "error",
          error,
        }]);
      });
    }

    // Check slot limit
    const filesToUpload = acceptedFiles.slice(0, remainingSlots);
    if (acceptedFiles.length > remainingSlots) {
      alert(`Only ${remainingSlots} upload slot(s) remaining. Some files were not uploaded.`);
    }

    // Upload each file
    for (const file of filesToUpload) {
      const uploadId = crypto.randomUUID();

      setUploadingFiles(prev => [...prev, {
        id: uploadId,
        filename: file.name,
        progress: 0,
        status: "uploading",
      }]);

      try {
        await apiClient.uploadFile("/api/documents/upload", file, (progress) => {
          setUploadingFiles(prev => prev.map(f =>
            f.id === uploadId ? { ...f, progress } : f
          ));
        });

        setUploadingFiles(prev => prev.map(f =>
          f.id === uploadId ? { ...f, status: "done", progress: 100 } : f
        ));

        onUploadComplete();
      } catch (error) {
        const message = error instanceof ApiError
          ? getErrorMessage(error.status)
          : "Upload failed. Please try again.";

        setUploadingFiles(prev => prev.map(f =>
          f.id === uploadId ? { ...f, status: "error", error: message } : f
        ));
      }
    }

    // Clear completed uploads after 3 seconds
    setTimeout(() => {
      setUploadingFiles(prev => prev.filter(f => f.status === "uploading"));
    }, 3000);
  }, [remainingSlots, onUploadComplete]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
    },
    maxFiles: remainingSlots,
    disabled: remainingSlots <= 0,
  });

  return (
    <div className="space-y-4">
      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer
          ${isDragActive ? "border-blue-500 bg-blue-50" : "border-gray-300 hover:border-gray-400"}
          ${remainingSlots <= 0 ? "opacity-50 cursor-not-allowed" : ""}`}
        role="button"
        tabIndex={0}
        aria-label="Upload documents. Press space or enter to select files."
      >
        <input {...getInputProps()} aria-label="File upload input" />
        <div className="space-y-2">
          <svg className="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48">
            <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          {isDragActive ? (
            <p className="text-blue-600 font-medium">Drop files here...</p>
          ) : remainingSlots <= 0 ? (
            <p className="text-gray-500">Maximum document limit reached</p>
          ) : (
            <>
              <p className="text-gray-700">Drag & drop documents here, or click to select</p>
              <p className="text-sm text-gray-500">PDF, DOCX (max {remainingSlots} files)</p>
            </>
          )}
        </div>
      </div>

      {/* Upload Progress */}
      {uploadingFiles.length > 0 && (
        <div className="space-y-2">
          {uploadingFiles.map(file => (
            <div key={file.id} className="border rounded-lg p-3 bg-gray-50">
              <div className="flex justify-between items-center mb-1">
                <span className="font-medium text-sm truncate max-w-[200px]">{file.filename}</span>
                <UploadStatusBadge status={file.status} />
              </div>

              {file.status === "uploading" && (
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${file.progress}%` }}
                    role="progressbar"
                    aria-valuenow={file.progress}
                    aria-valuemin={0}
                    aria-valuemax={100}
                  />
                </div>
              )}

              {file.error && (
                <p className="text-sm text-red-600 mt-1">{file.error}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function UploadStatusBadge({ status }: { status: UploadingFile["status"] }) {
  const config = {
    uploading: { label: "Uploading...", className: "bg-blue-100 text-blue-800" },
    done: { label: "Uploaded", className: "bg-green-100 text-green-800" },
    error: { label: "Failed", className: "bg-red-100 text-red-800" },
  };

  const { label, className } = config[status];
  return <span className={`px-2 py-0.5 text-xs rounded ${className}`}>{label}</span>;
}

function getErrorMessage(status: number): string {
  const messages: Record<number, string> = {
    400: "Invalid file or limit reached. Please check file format.",
    401: "Session expired. Please log in again.",
    413: "File is too large. Maximum size is 50MB.",
    500: "Server error. Please try again later.",
  };
  return messages[status] || "Upload failed. Please try again.";
}
