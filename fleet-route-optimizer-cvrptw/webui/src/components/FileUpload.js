import React, { useRef } from 'react';
import './FileUpload.css';

function FileUpload({ onFileLoad }) {
  const fileInputRef = useRef(null);

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const json = JSON.parse(e.target.result);
        onFileLoad(json);
      } catch (error) {
        alert('Invalid JSON file: ' + error.message);
      }
    };
    reader.readAsText(file);
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const handleDownloadExamples = async () => {
    try {
      const response = await fetch('http://localhost:8000/download-examples');
      if (!response.ok) {
        throw new Error('Failed to download examples');
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'cvrptw_examples.zip';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      alert('Error downloading examples: ' + error.message);
    }
  };

  return (
    <div className="file-upload">
      <input
        ref={fileInputRef}
        type="file"
        accept=".json"
        onChange={handleFileChange}
        style={{ display: 'none' }}
      />
      <button className="upload-button" onClick={handleClick}>
        📁 Load JSON File
      </button>
      <button className="download-example" onClick={handleDownloadExamples}>
        📥 Download Examples
      </button>
      <p className="upload-hint">Upload a problem file (JSON format) with customers, vehicles, and time windows</p>
    </div>
  );
}

export default FileUpload;
