import React, { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { TypingIndicator } from '@chatscope/chat-ui-kit-react';

interface ChatMessage {
  message_id: number;
  session_id: number;
  sender: 'bot' | 'user';
  content: string;
}

export interface SessionChatProps {
  inputRef: React.RefObject<HTMLInputElement>;
  message: string;
  setMessage: React.Dispatch<React.SetStateAction<string>>;
  isWaitingForBot: boolean;
  handleSend: () => void;
}

const SessionChat: React.FC<SessionChatProps> = ({
  inputRef,
  message,
  setMessage,
  isWaitingForBot,
  handleSend: _handleSend,
}) => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [isWaitingForResponse, setIsWaitingForResponse] = useState(true);
  const [messagesList, setMessagesList] = useState<ChatMessage[]>([]);
  const [showTyping, setShowTyping] = useState(false);
  const isInitializingRef = useRef(false);

  useEffect(() => {
    let isMounted = true;

    const initializeSession = async () => {
      if (!sessionId || isInitializingRef.current) return;

      isInitializingRef.current = true;
      setIsWaitingForResponse(true);

      try {
        const messagesPromise = fetch(`http://localhost:8000/chat/get-all-messages/${sessionId}`);
        const botCountPromise = fetch(`http://localhost:8000/chat/get-num-messages/${sessionId}/bot`);
        const userCountPromise = fetch(`http://localhost:8000/chat/get-num-messages/${sessionId}/user`);

        const [messagesRes, botCountRes, userCountRes] = await Promise.all([
          messagesPromise,
          botCountPromise,
          userCountPromise,
        ]);

        if (!messagesRes.ok || !botCountRes.ok || !userCountRes.ok) {
          throw new Error('failed to load data');
        }

        const existingMessages = await messagesRes.json();
        const botCount = await botCountRes.json();
        const userCount = await userCountRes.json();

        if (!isMounted) return;

        setMessagesList(existingMessages);

        const needsBotResponse = botCount === userCount;

        if (needsBotResponse) {
          setShowTyping(true);
          const response = await fetch(`http://localhost:8000/chat/${sessionId}/bot/new`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
          });

          if (!response.ok) {
            throw new Error('failed to fetch response.');
          }

          const botMessage = await response.json();
          if (isMounted) {
            setMessagesList((prev) => [...prev, botMessage]);
          }
        }
      } catch (error) {
        console.error('Error initializing session:', error);
      } finally {
        if (isMounted) {
          setShowTyping(false);
          setIsWaitingForResponse(false);
        }
        isInitializingRef.current = false;
      }
    };

    initializeSession();

    return () => {
      isMounted = false;
      isInitializingRef.current = false;
    };
  }, [sessionId]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (isWaitingForResponse || showTyping) {
      e.preventDefault();
      return;
    }
    setMessage(e.target.value);
  };

  const safeMessageContent = (msg: ChatMessage) => {
    if (msg.sender !== 'bot') return msg.content;

    try {
      const parsed = JSON.parse(msg.content);
      if (parsed && typeof parsed === 'object') {
        return parsed.content ?? msg.content;
      }
    } catch (_) {
      // fall back to raw message content if JSON parse fails
    }
    return msg.content;
  };

  const handleSend = async () => {
    if (!message.trim() || isWaitingForResponse || showTyping || !sessionId) {
      return;
    }

    const messageContent = message.trim();
    setMessage('');
    setIsWaitingForResponse(true);

    try {
      const userMessageRes = await fetch(`http://localhost:8000/chat/${sessionId}/new`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content: messageContent,
          sender: 'user',
        }),
      });

      if (!userMessageRes.ok) {
        throw new Error('Failed to send message');
      }

      const userMessage = await userMessageRes.json();
      setMessagesList((prev) => [...prev, userMessage]);

      setShowTyping(true);
      const botResponseRes = await fetch(`http://localhost:8000/chat/${sessionId}/bot/new`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!botResponseRes.ok) {
        throw new Error('Failed to get bot response');
      }

      const botMessage = await botResponseRes.json();
      setMessagesList((prev) => [...prev, botMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      setMessage(messageContent);
      alert('Failed to send message. Please try again.');
    } finally {
      setShowTyping(false);
      setIsWaitingForResponse(false);
    }
  };

  const handleInputKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (isWaitingForResponse || showTyping) {
      e.preventDefault();
      e.stopPropagation();
      return;
    }
    if (e.key === 'Enter') {
      handleSend();
    }
  };

  return (
    <div className="chat-container">
      <div className="messages-area">
        {messagesList.map((msg) => (
          <div
            key={msg.message_id}
            className={`message-row ${msg.sender === 'bot' ? 'bot' : 'user'}`}
          >
            {safeMessageContent(msg)}
          </div>
        ))}
        {showTyping && (
          <div className="message-row bot typing-row">
            <TypingIndicator />
          </div>
        )}
      </div>
      <div className="input-container">
        <input
          ref={inputRef}
          type="text"
          className="text-input"
          placeholder={isWaitingForResponse || showTyping ? 'Waiting for response...' : 'Type a message...'}
          value={isWaitingForResponse || showTyping ? '' : message}
          onChange={handleInputChange}
          onKeyPress={handleInputKeyPress}
          onKeyDown={(e) => {
            if (isWaitingForResponse || showTyping) {
              e.preventDefault();
              e.stopPropagation();
            }
          }}
          disabled={isWaitingForResponse || showTyping}
          readOnly={isWaitingForResponse || showTyping}
          tabIndex={isWaitingForResponse || showTyping ? -1 : 0}
        />
        <button
          className="send-button"
          onClick={handleSend}
          disabled={isWaitingForResponse || showTyping || !message.trim()}
        >
          Send
        </button>
      </div>
    </div>
  );
};

export default SessionChat;

