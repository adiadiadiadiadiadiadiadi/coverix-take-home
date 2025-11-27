import React, { useRef, useState } from 'react';
import { Routes, Route, useNavigate } from 'react-router-dom';
import '@chatscope/chat-ui-kit-styles/dist/default/styles.min.css';
import './App.css';
import SessionChat from './components/SessionChat';

function App() {
  const [message, setMessage] = useState('');
  const [isWaitingForBot, setIsWaitingForBot] = useState(false);
  const [sessionId, setSessionId] = useState(0);

  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const handleNewChat = async () => {
    setMessage('');

    try {
      const response = await fetch('http://localhost:8000/chat/new', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('chat could not be created. try again later.');
      }

      const newSessionId = await response.json();
      setSessionId(newSessionId);
      navigate(`/session/${newSessionId}`, { replace: true });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      alert(`Failed to create new chat: ${errorMessage}`);
    }
  };


  return (
    <div className="App">
      <Routes>
        <Route
          path="/new"
          element={
            <div className="chat-container">
              <div>loading...</div>
            </div>
          }
        />
        <Route
          path="/session/:sessionId"
          element={
            <SessionChat
              inputRef={inputRef}
              message={message}
              setMessage={setMessage}
              isWaitingForBot={isWaitingForBot}
              handleSend={() => {}} // Not used - SessionChat has its own handleSend
            />
          }
        />
        <Route
          path="/"
          element={
            <div className="chat-container">
              <button 
                className="new-chat-button home-page-button" 
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  handleNewChat();
                }}
                title="New Chat"
              >
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 16 16"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M8 3.5V12.5M3.5 8H12.5"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </button>
              <div style={{ padding: '2rem', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: '1rem' }}>
                <p 
                  className="click-to-start-text"
                  onClick={handleNewChat}
                  style={{ cursor: 'pointer', color: '#ffffff', fontSize: '18px', margin: 0 }}
                >
                  Click to get started
                </p>
              </div>
            </div>
          }
        />
      </Routes>
    </div>
  );
}

export default App;
