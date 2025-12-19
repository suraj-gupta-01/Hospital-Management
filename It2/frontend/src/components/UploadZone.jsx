import React, { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Upload, FileImage, X } from "lucide-react";
import axios from "axios";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const UploadZone = ({ onUploadSuccess }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  const onDrop = useCallback((acceptedFiles) => {
    const file = acceptedFiles[0];
    if (!file) return;

    // Validate file size (20 MB)
    if (file.size > 20 * 1024 * 1024) {
      toast.error("File size must be less than 20 MB");
      return;
    }

    // Validate file type
    if (!file.type.startsWith("image/")) {
      toast.error("File must be an image");
      return;
    }

    setSelectedFile(file);

    // Create preview
    const reader = new FileReader();
    reader.onload = () => {
      setPreview(reader.result);
    };
    reader.readAsDataURL(file);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "image/*": [".png", ".jpg", ".jpeg", ".webp"],
    },
    multiple: false,
    disabled: uploading,
  });

  const handleUpload = async () => {
    if (!selectedFile) {
      toast.error("Please select a file first");
      return;
    }

    setUploading(true);
    setUploadProgress(0);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      await axios.post(`${API}/upload-prescription`, formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = progressEvent.total
            ? Math.round((progressEvent.loaded * 100) / progressEvent.total)
            : 0;
          setUploadProgress(percentCompleted);
        },
      });

      toast.success("Prescription uploaded successfully! Processing...");
      setSelectedFile(null);
      setPreview(null);
      setUploadProgress(0);
      onUploadSuccess();
    } catch (error) {
      console.error("Upload error:", error);
      toast.error(error.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const clearSelection = () => {
    setSelectedFile(null);
    setPreview(null);
    setUploadProgress(0);
  };

  return (
    <Card data-testid="upload-card">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Upload className="h-5 w-5" />
          Upload Prescription
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Dropzone */}
        {!preview ? (
          <div
            {...getRootProps()}
            data-testid="dropzone"
            className={`
              border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors
              ${
                isDragActive
                  ? "border-blue-500 bg-blue-50"
                  : "border-slate-300 bg-slate-50 hover:border-slate-400"
              }
              ${uploading ? "opacity-50 cursor-not-allowed" : ""}
            `}
          >
            <input {...getInputProps()} />
            <FileImage className="mx-auto h-12 w-12 text-slate-400 mb-4" />
            <p className="text-lg font-medium text-slate-700">
              {isDragActive
                ? "Drop the image here"
                : "Drag & drop prescription image"}
            </p>
            <p className="text-sm text-slate-500 mt-2">
              or click to select file (PNG, JPG, WEBP • Max 20 MB)
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Preview */}
            <div className="relative border rounded-lg overflow-hidden" data-testid="image-preview">
              <img
                src={preview}
                alt="Preview"
                className="w-full h-64 object-contain bg-slate-100"
              />
              {!uploading && (
                <button
                  onClick={clearSelection}
                  data-testid="clear-button"
                  className="absolute top-2 right-2 p-2 bg-white rounded-full shadow-lg hover:bg-slate-100 transition-colors"
                >
                  <X className="h-4 w-4 text-slate-600" />
                </button>
              )}
            </div>

            {/* File Info */}
            <div className="bg-slate-50 p-3 rounded-lg">
              <p className="text-sm font-medium text-slate-700">
                {selectedFile?.name}
              </p>
              <p className="text-xs text-slate-500 mt-1">
                {(selectedFile?.size / 1024 / 1024).toFixed(2)} MB
              </p>
            </div>

            {/* Progress */}
            {uploading && (
              <div className="space-y-2">
                <Progress value={uploadProgress} className="h-2" data-testid="upload-progress" />
                <p className="text-sm text-slate-600 text-center">
                  Uploading... {uploadProgress}%
                </p>
              </div>
            )}

            {/* Upload Button */}
            <Button
              onClick={handleUpload}
              disabled={uploading}
              className="w-full"
              size="lg"
              data-testid="upload-button"
            >
              {uploading ? "Uploading..." : "Upload & Process"}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default UploadZone;
