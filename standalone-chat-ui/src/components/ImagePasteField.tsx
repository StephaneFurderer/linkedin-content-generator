"use client";

import { useState, useRef } from 'react';

interface ImagePasteFieldProps {
  value: string;
  onChange: (url: string) => void;
  placeholder?: string;
  className?: string;
}

export default function ImagePasteField({ 
  value, 
  onChange, 
  placeholder = "Paste image here (Cmd+V) or enter URL manually",
  className = ""
}: ImagePasteFieldProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const handlePaste = async (e: React.ClipboardEvent) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    // Look for image data in clipboard
    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.type.indexOf('image') !== -1) {
        e.preventDefault();
        
        const file = item.getAsFile();
        if (file) {
          await uploadImage(file);
        }
        return;
      }
    }
  };

  const uploadImage = async (file: File) => {
    setIsUploading(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('http://localhost:8000/upload-image', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Upload failed');
      }

      const result = await response.json();
      onChange(result.public_url);
      
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsUploading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Allow paste with Cmd+V or Ctrl+V
    if ((e.metaKey || e.ctrlKey) && e.key === 'v') {
      // The paste event will be handled by onPaste
    }
  };

  return (
    <div className="space-y-2">
      <div className="relative">
        <input
          ref={inputRef}
          type="url"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onPaste={handlePaste}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className={`w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${className}`}
          disabled={isUploading}
        />
        
        {isUploading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-75 rounded-md">
            <div className="flex items-center space-x-2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
              <span className="text-sm text-gray-600">Uploading...</span>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="text-sm text-red-600 bg-red-50 p-2 rounded">
          {error}
        </div>
      )}

      {value && !error && (
        <div className="space-y-2">
          <div className="text-sm text-green-600 bg-green-50 p-2 rounded">
            ✅ Image URL ready
          </div>
          <div className="max-w-xs">
            <img 
              src={value} 
              alt="Preview" 
              className="w-full h-auto rounded border"
              onError={() => setError('Invalid image URL')}
            />
          </div>
        </div>
      )}

      <div className="text-xs text-gray-500">
        💡 Tip: Take a screenshot (Cmd+Shift+4), then paste it directly here!
      </div>
    </div>
  );
}
