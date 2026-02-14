import { useState } from "react";
import Player from "./Player";

function App() {
  const [stage, setStage] = useState("auth"); // auth | login | player
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleLogin = () => {
    if (username === "admin" && password === "1234") {
      setStage("player");
      setError("");
    } else {
      setError("Invalid username or password");
    }
  };

  // 🔐 Authentication screen
  if (stage === "auth") {
    return (
      <div style={{ textAlign: "center", marginTop: "100px" }}>
        <h2>🔒 Authentication Required</h2>
        <button onClick={() => setStage("login")}>Sign In</button>
      </div>
    );
  }

  // 🧾 Login screen
  if (stage === "login") {
    return (
      <div style={{ textAlign: "center", marginTop: "100px" }}>
        <h2>Sign In</h2>

        <div>
          <input
            type="text"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </div>

        <div style={{ marginTop: "10px" }}>
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>

        <div style={{ marginTop: "15px" }}>
          <button onClick={handleLogin}>Login</button>
        </div>

        {error && (
          <p style={{ color: "red", marginTop: "10px" }}>{error}</p>
        )}
      </div>
    );
  }

  // 🎥 Video player
  return <Player />;
}

export default App;<q></q>