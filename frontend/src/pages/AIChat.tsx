import React, { useState, useRef, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { apiService } from '../services/apiService';
import { Button } from '../components/ui/Button';
import { Card, CardContent } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { useToast } from '../contexts/ToastContext';
import {
  Send,
  Bot,
  User,
  Sparkles,
  ArrowRight,
  Loader2,
  CheckCircle,
  TrendingUp,
  History,
  FileText
} from 'lucide-react';
import type { ChatMessage, ChatResponse } from '../types';

export const AIChat: React.FC = () => {
  const { showToast } = useToast();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const chatEndRef = useRef<HTMLDivElement>(null);

  const suggestedPrompts = [
    { text: 'Show my transactions', icon: History },
    { text: 'Analyze my spending', icon: TrendingUp },
    { text: 'Generate financial report', icon: FileText },
    { text: 'What is my balance?', icon: Sparkles }
  ];

  // Auto-scroll to bottom of chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const chatMutation = useMutation({
    mutationFn: apiService.sendChatMessage,
    onSuccess: (data: ChatResponse) => {
      // Add the assistant response message
      // We will look for report_agent summary or memory summary or a general summary
      let finalContent = '';
      
      if (data.report && data.report.status === 'completed' && data.report.summary) {
        finalContent = data.report.summary;
      } else if (data.finance && data.finance.status === 'completed' && data.finance.summary) {
        finalContent = data.finance.summary;
      } else if (data.budget && data.budget.status === 'completed' && data.budget.summary) {
        finalContent = data.budget.summary;
      } else if (data.goal && data.goal.status === 'completed' && data.goal.summary) {
        finalContent = data.goal.summary;
      } else if (data.memory && data.memory.summary) {
        finalContent = data.memory.summary;
      } else {
        finalContent = "I've processed your request but could not compile a summary.";
      }

      setMessages((prev) => [
        ...prev,
        {
          id: Math.random().toString(36).substring(2, 9),
          role: 'assistant',
          content: finalContent,
          timestamp: new Date(),
          metadata: data,
        },
      ]);
    },
    onError: (err: any) => {
      showToast(err.message || 'Failed to get a response from the AI.', 'error');
      // Add error message to chat
      setMessages((prev) => [
        ...prev,
        {
          id: Math.random().toString(36).substring(2, 9),
          role: 'assistant',
          content: "Sorry, I encountered an error while processing your request. Please try again.",
          timestamp: new Date(),
        },
      ]);
    },
  });

  const handleSendMessage = (messageText: string) => {
    const trimmed = messageText.trim();
    if (!trimmed) return;

    // Add user message
    const userMsg: ChatMessage = {
      id: Math.random().toString(36).substring(2, 9),
      role: 'user',
      content: trimmed,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputMessage('');

    // Trigger AI response
    chatMutation.mutate(trimmed);
  };

  // Render text content with simple markdown support
  const renderMarkdown = (text: string) => {
    // Simple replacement for bullet points, bold text, INR symbol, newlines
    const lines = text.split('\n');
    return lines.map((line, idx) => {
      let content: React.ReactNode = line;
      
      // Bold matching
      if (line.includes('**')) {
        const parts = line.split('**');
        content = parts.map((part, i) => (i % 2 === 1 ? <strong key={i} className="font-extrabold text-slate-800 dark:text-slate-100">{part}</strong> : part));
      }

      // Check if bullet point
      if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
        const bulletText = line.trim().substring(2);
        return (
          <li key={idx} className="ml-5 list-disc text-sm py-0.5 leading-relaxed text-slate-655 dark:text-slate-350">
            {bulletText.includes('**') ? (
              bulletText.split('**').map((part, i) => (i % 2 === 1 ? <strong key={i} className="font-extrabold text-slate-800 dark:text-slate-100">{part}</strong> : part))
            ) : (
              bulletText
            )}
          </li>
        );
      }

      return (
        <p key={idx} className="text-sm py-1 leading-relaxed text-slate-655 dark:text-slate-350 min-h-[1.5rem]">
          {content}
        </p>
      );
    });
  };

  return (
    <div className="h-[80vh] flex flex-col lg:flex-row gap-6 relative">
      {/* Sidebar: Suggested prompts and explanations */}
      <aside className="w-full lg:w-72 flex flex-col gap-4">
        <Card className="h-fit">
          <CardContent className="p-5 flex flex-col gap-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-indigo-650 flex items-center justify-center text-white">
                <Sparkles className="w-4 h-4" />
              </div>
              <h3 className="text-sm font-bold text-slate-800 dark:text-slate-150">Financial Agent</h3>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed">
              This assistant routes your queries through domain agents (Finance, Budgets, Goals, Reports) using LangGraph. It analyzes live database records to provide accurate recommendations.
            </p>
          </CardContent>
        </Card>

        <Card className="flex-1 flex flex-col">
          <CardContent className="p-5 flex flex-col gap-3">
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Suggested Prompts</h4>
            <div className="flex flex-col gap-2">
              {suggestedPrompts.map((prompt, idx) => {
                const Icon = prompt.icon;
                return (
                  <button
                    key={idx}
                    onClick={() => handleSendMessage(prompt.text)}
                    disabled={chatMutation.isPending}
                    className="flex items-center gap-3 p-3 rounded-xl border border-slate-150 dark:border-slate-800/60 bg-white/30 dark:bg-slate-900/10 hover:bg-slate-100 dark:hover:bg-slate-850/50 text-slate-700 dark:text-slate-300 text-xs font-bold text-left transition-all duration-200 group active:scale-98"
                  >
                    <Icon className="w-4 h-4 text-indigo-500 shrink-0" />
                    <span className="truncate flex-1">{prompt.text}</span>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-350 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </button>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </aside>

      {/* Main Chat Interface */}
      <Card className="flex-1 flex flex-col min-h-0">
        {/* Messages list */}
        <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6">
          {messages.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
              <Bot className="w-12 h-12 text-indigo-650 dark:text-indigo-400 mb-4 animate-bounce" />
              <h3 className="text-base font-bold text-slate-850 dark:text-slate-100">AI Financial Co-Pilot</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-2 max-w-sm">
                Ask me questions about your total balance, monthly transactions, savings progress, or request a complete financial report!
              </p>
            </div>
          ) : (
            messages.map((message) => {
              const isUser = message.role === 'user';
              return (
                <div
                  key={message.id}
                  className={`flex gap-3.5 ${isUser ? 'flex-row-reverse text-right' : 'text-left'}`}
                >
                  <div className={`w-8.5 h-8.5 rounded-full flex items-center justify-center shrink-0 shadow-sm ${
                    isUser
                      ? 'bg-indigo-600 text-white font-bold text-sm'
                      : 'bg-indigo-50 dark:bg-indigo-950/20 text-indigo-600 dark:text-indigo-400'
                  }`}>
                    {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4.5 h-4.5" />}
                  </div>

                  <div className="flex flex-col gap-2 max-w-[80%]">
                    {/* Speech Bubble */}
                    <div className={`p-4 rounded-2xl ${
                      isUser
                        ? 'bg-indigo-600 text-white text-sm font-semibold rounded-tr-none'
                        : 'bg-slate-50/70 dark:bg-slate-900/40 border border-slate-100 dark:border-slate-800/80 rounded-tl-none shadow-sm'
                    }`}>
                      {isUser ? (
                        <p className="text-sm text-left leading-relaxed">{message.content}</p>
                      ) : (
                        <div className="text-left">{renderMarkdown(message.content)}</div>
                      )}
                    </div>

                    {/* Agent planning details (shown on assistant responses) */}
                    {!isUser && message.metadata && (
                      <div className="flex flex-col gap-1.5 mt-1">
                        <div className="flex flex-wrap items-center gap-1.5 text-[10px] text-slate-400 font-semibold">
                          <span>Planned Agents:</span>
                          {message.metadata.planned_agents.length === 0 ? (
                            <Badge variant="secondary" className="text-[9px] px-1.5 py-0">None</Badge>
                          ) : (
                            message.metadata.planned_agents.map((agent) => (
                              <Badge key={agent} variant="primary" className="text-[9px] px-1.5 py-0 uppercase">
                                {agent}
                              </Badge>
                            ))
                          )}
                        </div>

                        {/* Domain node execution breakdowns */}
                        <div className="flex flex-col gap-1 pl-1">
                          {message.metadata.tool_results && message.metadata.tool_results.length > 0 && (
                            <details className="text-[10px] text-slate-450 dark:text-slate-500 font-medium">
                              <summary className="cursor-pointer hover:underline outline-none select-none font-bold">
                                View database tool queries ({message.metadata.tool_results.length})
                              </summary>
                              <div className="mt-1 flex flex-col gap-1 pl-3 border-l border-slate-200 dark:border-slate-850">
                                {message.metadata.tool_results.map((tool, idx) => (
                                  <div key={idx} className="flex items-center gap-1.5">
                                    <CheckCircle className="w-3 h-3 text-emerald-500 shrink-0" />
                                    <span>Executed: <span className="font-bold text-slate-600 dark:text-slate-405">{tool.tool}:{tool.action}</span></span>
                                  </div>
                                ))}
                              </div>
                            </details>
                          )}
                        </div>
                      </div>
                    )}

                    <span className="text-[9px] text-slate-400/80 font-medium mt-1">
                      {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                </div>
              );
            })
          )}

          {chatMutation.isPending && (
            <div className="flex gap-3.5 text-left">
              <div className="w-8.5 h-8.5 rounded-full bg-indigo-50 dark:bg-indigo-950/20 text-indigo-600 dark:text-indigo-400 flex items-center justify-center shrink-0">
                <Bot className="w-4.5 h-4.5" />
              </div>
              <div className="flex flex-col gap-2 max-w-[80%]">
                <div className="p-4 bg-slate-50/70 dark:bg-slate-900/40 border border-slate-100 dark:border-slate-800/80 rounded-2xl rounded-tl-none flex items-center gap-2 shadow-sm">
                  <Loader2 className="w-4 h-4 animate-spin text-indigo-650" />
                  <span className="text-xs text-slate-500 font-medium">Assistant is thinking...</span>
                </div>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Input box */}
        <div className="p-4 border-t border-slate-150 dark:border-slate-800/60 bg-white/20 dark:bg-slate-900/5 backdrop-blur-sm rounded-b-2xl">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage(inputMessage);
            }}
            className="flex gap-2"
          >
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              disabled={chatMutation.isPending}
              placeholder="Ask anything (e.g. 'Generate financial report' or 'Compare budget to spend')"
              className="flex-1 px-4 py-3 rounded-xl border border-slate-350 dark:border-slate-850 bg-white/50 dark:bg-slate-900/50 text-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all"
            />
            <Button
              type="submit"
              disabled={chatMutation.isPending || !inputMessage.trim()}
              className="px-4 shrink-0 rounded-xl"
            >
              <Send className="w-4.5 h-4.5" />
            </Button>
          </form>
        </div>
      </Card>
    </div>
  );
};
export default AIChat;
