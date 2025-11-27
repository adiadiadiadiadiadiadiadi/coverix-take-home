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
}

const SessionChat: React.FC<SessionChatProps> = ({
  inputRef,
  message,
  setMessage
}) => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [isWaitingForResponse, setIsWaitingForResponse] = useState(true);
  const [messagesList, setMessagesList] = useState<ChatMessage[]>([]);
  const [showTyping, setShowTyping] = useState(false);
  const isInitializingRef = useRef(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesAreaRef = useRef<HTMLDivElement>(null);

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

  const safeMessageContent = (msg: ChatMessage) => {
    if (msg.sender !== 'bot') return msg.content;

    try {
      const parsed = JSON.parse(msg.content);
      if (parsed && typeof parsed === 'object') {
        return parsed.content ?? msg.content;
      }
    } catch (_) {}
    return msg.content;
  };

  const isComplete = React.useMemo(() => {
    if (messagesList.length === 0) return false;
    const lastMessage = messagesList[messagesList.length - 1];
    if (lastMessage.sender === 'bot') {
      const content = safeMessageContent(lastMessage).toLowerCase();
      return content.includes('connecting you to an agent') || 
             content.includes("connecting you to a human agent") ||
             content.includes("i'm connecting you to") ||
             content.includes("connecting you to") ||
             content.includes("connect you to") ||
             content.includes("connect to an agent") ||
             content.includes("connect to a human");
    }
    return false;
  }, [messagesList]);

  useEffect(() => {
    if (isComplete) {
      setMessage('');
    }
  }, [isComplete, setMessage]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (isWaitingForResponse || showTyping || isComplete) {
      e.preventDefault();
      e.stopPropagation();
      return;
    }
    setMessage(e.target.value);
  };

  const handleSend = async () => {
    if (!message.trim() || isWaitingForResponse || showTyping || !sessionId || isComplete) {
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
      setMessage(messageContent);
      alert('Failed to send message. Please try again.');
    } finally {
      setShowTyping(false);
      setIsWaitingForResponse(false);
    }
  };

  const handleInputKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (isWaitingForResponse || showTyping || isComplete) {
      e.preventDefault();
      e.stopPropagation();
      return;
    }
    if (e.key === 'Enter') {
      handleSend();
    }
  };

  const isInputDisabled = isWaitingForResponse || showTyping || isComplete;

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messagesList, showTyping]);

  // Focus input when AI is done speaking
  useEffect(() => {
    if (!showTyping && !isWaitingForResponse && !isComplete && inputRef.current) {
      inputRef.current.focus();
    }
  }, [showTyping, isWaitingForResponse, isComplete]);

  return (
    <div className="chat-container">
      <div className="messages-area" ref={messagesAreaRef}>
        {messagesList.map((msg) => {
          const content = safeMessageContent(msg);
          return (
            <div
              key={msg.message_id}
              className={`message-row ${msg.sender === 'bot' ? 'bot' : 'user'}`}
            >
              {content.split('\n').map((line: string, index: number, array: string[]) => (
                <React.Fragment key={index}>
                  {line}
                  {index < array.length - 1 && <br />}
                </React.Fragment>
              ))}
            </div>
          );
        })}
        {showTyping && (
          <div className="message-row bot typing-row">
            <TypingIndicator />
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <div className="input-container">
        <input
          ref={inputRef}
          type="text"
          className="text-input"
          placeholder={isInputDisabled ? (isComplete ? 'Connected to agent - conversation complete' : 'Waiting for response...') : 'Type a message...'}
          value={isInputDisabled ? '' : message}
          onChange={handleInputChange}
          onKeyPress={handleInputKeyPress}
          onKeyDown={(e) => {
            if (isInputDisabled) {
              e.preventDefault();
              e.stopPropagation();
              return false;
            }
          }}
          onPaste={(e) => {
            if (isInputDisabled) {
              e.preventDefault();
              e.stopPropagation();
            }
          }}
          disabled={isInputDisabled}
          readOnly={isInputDisabled}
          tabIndex={isInputDisabled ? -1 : 0}
          style={{ cursor: isInputDisabled ? 'not-allowed' : 'text' }}
        />
        <button
          className="send-button"
          onClick={handleSend}
          disabled={isInputDisabled || !message.trim()}
        >
          Send
        </button>
      </div>
    </div>
  );
};

export default SessionChat;

