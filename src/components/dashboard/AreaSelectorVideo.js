import React, { useEffect, useRef, useState } from 'react';

const AreaSelectorVideo = ({ videoSrc, onSave, onCancel, signalId, existingPoints = [] }) => {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [points, setPoints] = useState(existingPoints);
  const [isVideoLoaded, setIsVideoLoaded] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');

  // Update points when existingPoints or signalId changes
  useEffect(() => {
    setPoints(existingPoints);
  }, [existingPoints, signalId]);

  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.load();
    }
  }, [videoSrc]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');

    const draw = () => {
      if (!canvas || !ctx) return;

      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      // Draw the video frame
      if (videoRef.current && isVideoLoaded) {
        ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
      }

      // Draw the points and lines
      ctx.strokeStyle = 'yellow';
      ctx.lineWidth = 2;
      ctx.fillStyle = 'red';
      ctx.font = '12px sans-serif';

      points.forEach((pt, i) => {
        ctx.beginPath();
        ctx.arc(pt[0], pt[1], 5, 0, 2 * Math.PI);
        ctx.fill();
        ctx.fillText(`${i + 1}`, pt[0] + 8, pt[1] + 8);
      });

      if (points.length > 1) {
        ctx.beginPath();
        ctx.moveTo(points[0][0], points[0][1]);
        points.slice(1).forEach(pt => ctx.lineTo(pt[0], pt[1]));
        if (points.length === 4) {
          ctx.lineTo(points[0][0], points[0][1]);
        }
        ctx.stroke();
      }

      requestAnimationFrame(draw);
    };

    draw();
  }, [points, isVideoLoaded]);

  const handleClick = (e) => {
    if (points.length >= 4) return;
    
    const rect = canvasRef.current.getBoundingClientRect();
    const x = Math.round(e.clientX - rect.left);
    const y = Math.round(e.clientY - rect.top);
    setPoints([...points, [x, y]]);
  };

  const handleVideoLoad = () => {
    setIsVideoLoaded(true);
  };

  const handleSave = () => {
    if (points.length !== 4) {
      setError('Please select exactly 4 points');
      return;
    }
    setError('');
    onSave(points);
  };

  const handleReset = () => {
    setPoints([]);
  };

  const handleCancel = () => {
    onCancel();
  };

  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ position: 'relative', display: 'inline-block' }}>
        <video
          ref={videoRef}
          src={videoSrc}
          width="640"
          height="360"
          controls
          autoPlay
          muted
          onLoadedData={handleVideoLoad}
          style={{ border: '2px solid #333' }}
        />
        <canvas
          ref={canvasRef}
          width="640"
          height="360"
          onClick={handleClick}
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            cursor: points.length >= 4 ? 'not-allowed' : 'crosshair',
          }}
        />
      </div>
      <div style={{ marginTop: '1rem' }}>
        {error && (
          <p style={{ color: '#e74c3c', marginBottom: '1rem' }}>
            ⚠️ {error}
          </p>
        )}
        <p style={{ color: '#666', marginBottom: '1rem' }}>
          Click on the video to add exactly 4 points to form a quadrilateral area.
          {points.length > 0 && (
            <span style={{ color: points.length === 4 ? '#4CAF50' : '#FFA500' }}>
              {` (${points.length}/4 points)`}
            </span>
          )}
        </p>
        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
          <button 
            onClick={handleSave} 
            className="control-btn green"
            disabled={points.length !== 4 || isSaving}
          >
            {isSaving ? '💾 Saving...' : '✅ Save Area'}
          </button>
          <button 
            onClick={handleReset} 
            className="control-btn blue"
            disabled={points.length === 0 || isSaving}
          >
            ♻️ Reset
          </button>
          <button 
            onClick={handleCancel} 
            className="control-btn red"
            disabled={isSaving}
          >
            ❌ Cancel
          </button>
        </div>
      </div>
    </div>
  );
};

export default AreaSelectorVideo;
