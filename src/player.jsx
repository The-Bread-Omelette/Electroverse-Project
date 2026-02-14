import { useRef, useState, useEffect } from "react";

function Player() {
  const videoRef = useRef(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  // Play / Pause
  const playPause = () => {
    const video = videoRef.current;
    video.paused ? video.play() : video.pause();
  };

  // Stop
  const stopVideo = () => {
    const video = videoRef.current;
    video.pause();
    video.currentTime = 0;
  };

  // Skip seconds
  const skip = (sec) => {
    const video = videoRef.current;
    video.currentTime = Math.min(
      Math.max(0, video.currentTime + sec),
      duration
    );
  };

  // Update time while playing
  const updateTime = () => {
    setCurrentTime(videoRef.current.currentTime);
  };

  // Get video duration
  const loaded = () => {
    setDuration(videoRef.current.duration);
  };

  // Seek from slider
  const seek = (e) => {
    videoRef.current.currentTime = e.target.value;
    setCurrentTime(e.target.value);
  };

  // Format time mm:ss
  const formatTime = (time) => {
    const min = Math.floor(time / 60);
    const sec = Math.floor(time % 60);
    return `${min}:${sec < 10 ? "0" : ""}${sec}`;
  };

  return (
    <div style={{ textAlign: "center", marginTop: "20px" }}>
      <h2>My React Video Player</h2>

      <video
        ref={videoRef}
        width="600"
        src="/video.mp4"
        onTimeUpdate={updateTime}
        onLoadedMetadata={loaded}
      />

      {/* Timeline */}
      <div style={{ width: "600px", margin: "10px auto" }}>
        <input
          type="range"
          min="0"
          max={duration}
          value={currentTime}
          onChange={seek}
          style={{ width: "100%" }}
        />
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <span>{formatTime(currentTime)}</span>
          <span>{formatTime(duration)}</span>
        </div>
      </div>

      {/* Controls */}
      <div style={{ marginTop: "10px" }}>
        <button onClick={() => skip(-5)}>⏪ -5s</button>
        <button onClick={playPause} style={{ margin: "0 10px" }}>
          Play / Pause
        </button>
        <button onClick={() => skip(5)}>⏩ +5s</button>
        <button onClick={stopVideo} style={{ marginLeft: "10px" }}>
          Stop
        </button>
      </div>
    </div>
  );
}

export default Player;
