import React, { useState } from 'react';

const VideoSourceConfig = ({ onSave, onCancel, junctionId }) => {
  const [videoFiles, setVideoFiles] = useState({
    A: null,
    B: null,
    C: null,
    D: null
  });
  const [videoSources, setVideoSources] = useState({
    A: '',
    B: '',
    C: '',
    D: ''
  });
  const [uploadStatus, setUploadStatus] = useState({
    status: 'idle',
    message: ''
  });

  const handleFileChange = (signal, file) => {
    if (file) {
      console.log(`[DEBUG] Selected file for Signal ${signal}:`, {
        fileName: file.name,
        fileSize: file.size,
        fileType: file.type
      });

      setVideoFiles(prev => ({
        ...prev,
        [signal]: file
      }));

      // Create a temporary URL for preview
      const localURL = URL.createObjectURL(file);
      setVideoSources(prev => ({
        ...prev,
        [signal]: localURL
      }));
    }
  };

  const handleSave = async () => {
    const selectedFiles = Object.entries(videoFiles).filter(([_, file]) => file !== null);
    if (selectedFiles.length === 0) {
      setUploadStatus({
        status: 'error',
        message: 'Please select at least one video file'
      });
      return;
    }

    setUploadStatus({
      status: 'uploading',
      message: 'Uploading and processing videos...'
    });

    try {
      const newSources = { ...videoSources };
      for (const [signal, file] of selectedFiles) {
        const formData = new FormData();
        formData.append('video_file', file);
        formData.append('signal_id', signal);
        // POST to /api/upload_video/
        const response = await fetch('/api/upload_video/', {
          method: 'POST',
          body: formData
        });
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.error || `Upload failed for Signal ${signal}`);
        }
        // Optionally, you could parse the response for a file path or URL
        // For now, just use a local preview
        newSources[signal] = videoSources[signal];
      }
      setVideoSources(newSources);
      onSave(newSources);
      setUploadStatus({
        status: 'success',
        message: 'All videos uploaded successfully!'
      });
    } catch (err) {
      console.error('[ERROR] Upload failed:', err);
      setUploadStatus({
        status: 'error',
        message: err.message || 'Failed to upload videos'
      });
    }
  };

  return (
    <div className="modal-content">
      <h2>Configure Video Sources</h2>
      {uploadStatus.status === 'uploading' ? (
        <div style={{ textAlign: 'center', padding: '2rem' }}>
          <div className="upload-status uploading" style={{ fontSize: '1.2rem' }}>
            ⏳ Uploading and processing videos...
          </div>
        </div>
      ) : (
        <>
          <div
            className="video-source-config"
            style={{ maxHeight: '350px', overflowY: 'auto', marginBottom: '1rem' }}
          >
            {Object.entries(videoFiles).map(([signal, file]) => (
              <div key={signal} className="video-source-input">
                <label>Signal {signal} Video Source</label>
                <input
                  type="file"
                  accept="video/*"
                  onChange={(e) => handleFileChange(signal, e.target.files[0])}
                  disabled={uploadStatus.status === 'uploading'}
                />
                {videoSources[signal] && (
                  <video
                    src={videoSources[signal]}
                    controls
                    style={{ width: '100%', maxHeight: '150px', marginTop: '0.5rem' }}
                  />
                )}
              </div>
            ))}
          </div>
          {uploadStatus.message && uploadStatus.status !== 'uploading' && (
            <div
              className={`upload-status ${uploadStatus.status}`}
              style={{ margin: '1rem 0', padding: '0.5rem', textAlign: 'center' }}
            >
              {uploadStatus.status === 'success'
                ? '✅'
                : '❌'}{' '}
              {uploadStatus.message}
            </div>
          )}
          <div className="modal-actions">
            <button
              onClick={onCancel}
              className="control-btn gray"
              disabled={uploadStatus.status === 'uploading'}
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="control-btn green"
              disabled={
                uploadStatus.status === 'uploading' ||
                Object.values(videoFiles).every((f) => f === null)
              }
            >
              💾 Save Configuration
            </button>
          </div>
        </>
      )}
    </div>
  );
};

export default VideoSourceConfig;
