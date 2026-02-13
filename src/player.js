import React, { useRef } from "react";

function App() {
  const videoRef = useRef(null);

  const playPause = () => {
    const video = videoRef.current;
    if (video.paused) {
      video.play();
    } else {
      video.pause();
    }
  };

  const stopVideo = () => {
    const video = videoRef.current;
    video.pause();
    video.currentTime = 0;
  };

  return (
    <div style={{ textAlign: "center", marginTop: "20px" }}>
      <h2>My React Video Player</h2>

      <video
        ref={videoRef}
        width="600"
        src="/video.mp4"
      />

      <div style={{ marginTop: "10px" }}>
        <button onClick={playPause}>Play / Pause</button>
        <button onClick={stopVideo} style={{ marginLeft: "10px" }}>
          Stop</button>
      </div>
    </div>
  );
}

export default App;