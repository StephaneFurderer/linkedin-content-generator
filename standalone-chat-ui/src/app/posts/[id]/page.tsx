"use client";

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { supabase } from '@/lib/supabase';

interface Message {
  id: string;
  role: string;
  content: string;
  agent_name: string | null;
  created_at: string;
}

interface Conversation {
  id: string;
  title: string;
  status: string;
  summary: string | null;
  state: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export default function PostDetailPage() {
  const params = useParams();
  const conversationId = params.id as string;
  
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedFormat, setSelectedFormat] = useState('');
  const [isFormatting, setIsFormatting] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch conversation details
        const { data: convData, error: convError } = await supabase
          .from('conversations')
          .select('*')
          .eq('id', conversationId)
          .single();

        if (convError) throw convError;
        setConversation(convData);

        // Fetch messages
        const { data: msgData, error: msgError } = await supabase
          .from('messages')
          .select('*')
          .eq('conversation_id', conversationId)
          .order('created_at', { ascending: true });

        if (msgError) throw msgError;
        setMessages(msgData || []);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    };

    if (conversationId) {
      fetchData();
    }
  }, [conversationId]);

  const handleFormatWithTemplate = async () => {
    if (!selectedFormat || !conversationId) return;

    setIsFormatting(true);
    try {
      // Get the latest Writer message as the draft
      const writerMessage = messages.find(msg => msg.agent_name === 'Writer');
      if (!writerMessage) {
        alert('No Writer content found to format');
        return;
      }

      const response = await fetch('http://127.0.0.1:8000/format-agent/transform', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          conversation_id: conversationId,
          draft: writerMessage.content,
          category: conversation?.state?.category,
          format: selectedFormat,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to format content');
      }

      // const data = await response.json(); // Unused variable removed
      
      // Refresh the messages to show the new formatted content
      const { data: msgData, error: msgError } = await supabase
        .from('messages')
        .select('*')
        .eq('conversation_id', conversationId)
        .order('created_at', { ascending: true });

      if (msgError) throw msgError;
      setMessages(msgData || []);
      
      alert('Content formatted successfully!');
    } catch (error) {
      console.error('Error:', error);
      alert('Failed to format content. Make sure the backend server is running.');
    } finally {
      setIsFormatting(false);
    }
  };

  if (loading) {
    return <div className="container mx-auto p-4 text-center">Loading...</div>;
  }

  if (error) {
    return <div className="container mx-auto p-4 text-red-500">Error: {error}</div>;
  }

  if (!conversation) {
    return <div className="container mx-auto p-4">Conversation not found</div>;
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-800';
      case 'waiting_for_approval': return 'bg-yellow-100 text-yellow-800';
      case 'in_progress': return 'bg-blue-100 text-blue-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="container mx-auto p-4">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2 text-gray-900">{conversation.title}</h1>
        <div className="flex items-center gap-4 text-sm text-gray-900">
          <span className={`px-2 py-1 rounded-full text-xs font-semibold ${getStatusColor(conversation.status)}`}>
            {conversation.status.replace(/_/g, ' ')}
          </span>
          <span>Created: {new Date(conversation.created_at).toLocaleString()}</span>
          <span>Updated: {new Date(conversation.updated_at).toLocaleString()}</span>
        </div>
      </div>

      {conversation.summary && (
        <div className="bg-blue-50 p-4 rounded-lg mb-6">
          <h2 className="text-lg font-semibold mb-2 text-gray-900">Conversation Summary</h2>
          <p className="text-gray-900">{conversation.summary}</p>
        </div>
      )}

      {/* Format Selection */}
      {messages.some(msg => msg.agent_name === 'Writer') && (
        <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4 text-gray-900">Re-format Content</h2>
          <div className="flex items-center gap-4">
            <select
              value={selectedFormat}
              onChange={(e) => setSelectedFormat(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              disabled={isFormatting}
            >
              <option value="">Select format...</option>
              <option value="belief_shift">Belief Shift</option>
              <option value="origin_story">Origin Story</option>
              <option value="industry_myths">Industry Myths</option>
              <option value="framework">Framework</option>
              <option value="step_by_step">Step-by-step</option>
              <option value="how_i_how_to">How I / How to</option>
              <option value="objection_post">Objection Post</option>
              <option value="result_breakdown">Result Breakdown</option>
              <option value="client_success_story">Client Success Story</option>
            </select>
            <button
              onClick={handleFormatWithTemplate}
              disabled={!selectedFormat || isFormatting}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-bold py-2 px-4 rounded"
            >
              {isFormatting ? 'Formatting...' : 'Apply Format'}
            </button>
          </div>
          <p className="text-sm text-gray-600 mt-2">
            Select a format to transform the Writer&apos;s content into a structured LinkedIn post.
          </p>
        </div>
      )}

      <div className="bg-white shadow-md rounded-lg">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">Messages</h2>
        </div>
        <div className="divide-y divide-gray-200">
          {messages.map((message) => (
            <div key={message.id} className="p-6">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-1 rounded text-xs font-semibold ${
                    message.role === 'user' ? 'bg-blue-100 text-blue-800' :
                    message.role === 'assistant' ? 'bg-green-100 text-green-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {message.role}
                  </span>
                  {message.agent_name && (
                    <span className="px-2 py-1 rounded text-xs font-semibold bg-purple-100 text-purple-800">
                      {message.agent_name}
                    </span>
                  )}
                </div>
                <span className="text-sm text-gray-900">
                  {new Date(message.created_at).toLocaleString()}
                </span>
              </div>
              <div className="prose max-w-none">
                <p className="whitespace-pre-wrap text-gray-900">{message.content}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {conversation.state && Object.keys(conversation.state).length > 0 && (
        <div className="mt-6 bg-gray-50 p-4 rounded-lg">
          <h2 className="text-lg font-semibold mb-2 text-gray-900">Conversation State</h2>
          <pre className="text-sm text-gray-900 overflow-auto">
            {JSON.stringify(conversation.state, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
