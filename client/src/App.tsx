import React, { useRef, useState } from 'react';
import { Routes, Route, useNavigate } from 'react-router-dom';
import '@chatscope/chat-ui-kit-styles/dist/default/styles.min.css';
import './App.css';
import SessionChat from './components/SessionChat';

interface Conversation {
  id: string;
  title: string;
  session_id: number;
}

function App() {
  const [message, setMessage] = useState('');
  const [selectedConversation, setSelectedConversation] = useState<string | null>(null);
  const [isWaitingForBot, setIsWaitingForBot] = useState(false);
  const [sessionId, setSessionId] = useState(0);

  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const conversations: Conversation[] = [
    {
      id: '1',
      title: 'Vehicle Registration Help',
      session_id: 1,
    },
    {
      id: '2',
      title: 'Insurance Quote Inquiry',
      session_id: 2,
    },
    {
      id: '3',
      title: 'License Verification',
      session_id: 3,
    },
  ];

  const handleNewChat = async () => {
    setSelectedConversation(null);
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
      alert(error);
    }
  };


  return (
    <div className="App">
      <div className="sidebar">
        <button className="new-chat-button" onClick={handleNewChat}>
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
        <div className="conversations-list">
          {conversations.map((conv) => (
            <div
              key={conv.id}
              className={`conversation-item ${selectedConversation === conv.id ? 'active' : ''}`}
              onClick={() => {
                setSelectedConversation(conv.id);
                navigate(`/session/${conv.session_id}`);
              }}
            >
              <span className="conversation-title">{conv.title}</span>
            </div>
          ))}
        </div>
      </div>
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
              <div style={{ padding: '2rem', textAlign: 'center' }}>
                <p>Select a conversation or create a new chat to get started.</p>
              </div>
            </div>
          }
        />
      </Routes>
    </div>
  );
}

export default App;
