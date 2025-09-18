'use client'

import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'

interface Conversation {
  id: string
  title: string
  status: string
  created_at: string
  updated_at: string
  state: any
}

export default function Posts() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchConversations = async () => {
      try {
        const { data, error } = await supabase
          .from('conversations')
          .select('id, title, status, created_at, updated_at, state')
          .order('updated_at', { ascending: false })

        if (error) {
          throw error
        }

        setConversations(data || [])
      } catch (err) {
        console.error('Error fetching conversations:', err)
        setError('Failed to load conversations. Check your Supabase configuration.')
      } finally {
        setIsLoading(false)
      }
    }

    fetchConversations()
  }, [])

  const getStatusBadge = (status: string, state: any) => {
    if (status === 'completed' || state?.user_satisfied) {
      return <span className="inline-block bg-green-100 text-green-800 text-xs font-medium px-2.5 py-0.5 rounded">Completed</span>
    }
    if (state?.waiting_for_user) {
      return <span className="inline-block bg-yellow-100 text-yellow-800 text-xs font-medium px-2.5 py-0.5 rounded">Waiting for approval</span>
    }
    if (state?.status === 'in_progress') {
      return <span className="inline-block bg-blue-100 text-blue-800 text-xs font-medium px-2.5 py-0.5 rounded">In progress</span>
    }
    return <span className="inline-block bg-gray-100 text-gray-800 text-xs font-medium px-2.5 py-0.5 rounded">{status}</span>
  }

  if (isLoading) {
    return (
      <div className="px-4 py-6 sm:px-0">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-3xl font-bold text-gray-900 mb-8">My Posts</h1>
          <div className="text-center py-8">
            <div className="text-gray-900">Loading conversations...</div>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="px-4 py-6 sm:px-0">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-3xl font-bold text-gray-900 mb-8">My Posts</h1>
          <div className="text-center py-8">
            <div className="text-red-500">{error}</div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="px-4 py-6 sm:px-0">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">My Posts</h1>
        
        {conversations.length === 0 ? (
          <div className="text-center py-8">
            <div className="text-gray-900">No conversations yet. <a href="/generate-post" className="text-blue-600 hover:text-blue-800">Generate your first post</a></div>
          </div>
        ) : (
          <div className="bg-white shadow overflow-hidden sm:rounded-md">
            <ul className="divide-y divide-gray-200">
              {conversations.map((conversation) => (
                <li key={conversation.id}>
                  <div className="px-4 py-4 sm:px-6">
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <h3 className="text-lg font-medium text-gray-900 truncate">
                          {conversation.title}
                        </h3>
                        <div className="mt-1 flex items-center space-x-4 text-sm text-gray-900">
                          <span>Created: {new Date(conversation.created_at).toLocaleDateString()}</span>
                          <span>Updated: {new Date(conversation.updated_at).toLocaleDateString()}</span>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        {getStatusBadge(conversation.status, conversation.state)}
                        <a
                          href={`/posts/${conversation.id}`}
                          className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                        >
                          View →
                        </a>
                      </div>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}
