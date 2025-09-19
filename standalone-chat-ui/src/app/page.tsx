'use client'

import { useState, useEffect } from 'react'
import { supabase } from '@/lib/supabase'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'

type PanelMode = 'closed' | 'default' | 'expanded'

interface Conversation {
  id: string
  title: string
  status: string
  created_at: string
  updated_at: string
  state: Record<string, unknown> | null
}

export default function HomePage() {
  const [panel1Mode, setPanel1Mode] = useState<PanelMode>('default')
  const [panel2Mode, setPanel2Mode] = useState<PanelMode>('default')
  const [panel3Mode, setPanel3Mode] = useState<PanelMode>('default')
  
  // Posts data for Panel 1
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isAddingPost, setIsAddingPost] = useState(false)
  const [newPostTitle, setNewPostTitle] = useState('')
  const [newPostContent, setNewPostContent] = useState('')
  const [newPostTags, setNewPostTags] = useState('')
  const [isCreatingPost, setIsCreatingPost] = useState(false)
  
  // Panel 2: Chat state
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null)
  const [messages, setMessages] = useState<any[]>([])
  const [isLoadingMessages, setIsLoadingMessages] = useState(false)
  const [selectedFormat, setSelectedFormat] = useState('')
  const [isFormatting, setIsFormatting] = useState(false)
  const [feedbackText, setFeedbackText] = useState('')
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false)
  const [showFeedbackTab, setShowFeedbackTab] = useState(false)
  const [showTemplateTab, setShowTemplateTab] = useState(false)
  
  // Panel 3: Writing state
  const [finalContent, setFinalContent] = useState('')
  const [postStatus, setPostStatus] = useState('')
  const [isSavingPost, setIsSavingPost] = useState(false)

  // Fetch conversations on component mount
  useEffect(() => {
    fetchConversations()
  }, [])

  // Helper function for status badges
  const getStatusBadge = (status: string, state: Record<string, unknown> | null) => {
    if (status === 'archived') {
      return <Badge variant="outline" className="border-gray-500 text-gray-500">📦</Badge>
    }
    if (status === 'active') {
      return <Badge variant="default" className="bg-green-600 hover:bg-green-700">✓</Badge>
    }
    // Fallback for any other status or state-based logic
    if (state?.user_satisfied) {
      return <Badge variant="default" className="bg-green-600 hover:bg-green-700">✓</Badge>
    }
    if (state?.waiting_for_user) {
      return <Badge variant="secondary" className="bg-yellow-600 hover:bg-yellow-700">⏳</Badge>
    }
    if (state?.status === 'in_progress') {
      return <Badge variant="outline" className="border-blue-500 text-blue-500">🔄</Badge>
    }
    return <Badge variant="outline">📝</Badge>
  }

  // Handle Add Post mode - when adding a post, Panel 1 should be expanded
  const handleAddPost = () => {
    setIsAddingPost(true)
    setPanel1Mode('expanded')
  }

  const handleCancelAddPost = () => {
    setIsAddingPost(false)
    setPanel1Mode('default')
    // Reset form fields
    setNewPostTitle('')
    setNewPostContent('')
    setNewPostTags('')
  }

  const handleCreatePost = async () => {
    if (!newPostTitle.trim() || !newPostContent.trim()) {
      alert('Please fill in both title and content')
      return
    }

    setIsCreatingPost(true)
    try {
      // Use the backend API to create a conversation instead of direct Supabase insert
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/coordinator/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_request: newPostContent.trim(),
          conversation_title: newPostTitle.trim(),
          category: 'manual_post'
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(`Failed to create post: ${response.status} ${response.statusText}`)
      }

      const result = await response.json()
      console.log('Post created successfully:', result)

      // Refresh the conversations list
      await fetchConversations()
      
      // Reset form and return to default mode
      handleCancelAddPost()
      
      alert('Post created successfully!')
    } catch (err) {
      console.error('Error creating post:', err)
      alert(`Failed to create post: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setIsCreatingPost(false)
    }
  }

  // Handle conversation selection for Panel 2
  const handleConversationSelect = async (conversation: Conversation) => {
    setSelectedConversation(conversation)
    setIsLoadingMessages(true)
    
    try {
      const { data, error } = await supabase
        .from('messages')
        .select('*')
        .eq('conversation_id', conversation.id)
        .order('created_at', { ascending: true })

      if (error) {
        throw error
      }

      setMessages(data || [])
      
      // Load the latest formatted content into Panel 3
      loadLatestFormattedContent(data || [])
      
      // Set the current post status
      setPostStatus(conversation.status || 'draft')
    } catch (err) {
      console.error('Error fetching messages:', err)
      setMessages([])
    } finally {
      setIsLoadingMessages(false)
    }
  }

  // Load the latest formatted content for Panel 3
  const loadLatestFormattedContent = (messages: any[]) => {
    // Find the latest Format Agent message (most recent formatted content)
    const formatAgentMessages = messages.filter(msg => msg.agent_name === 'Format Agent')
    if (formatAgentMessages.length > 0) {
      const latestFormatMessage = formatAgentMessages[formatAgentMessages.length - 1]
      setFinalContent(latestFormatMessage.content || '')
    } else {
      // Fallback to latest Writer message if no Format Agent content
      const writerMessages = messages.filter(msg => msg.agent_name === 'Writer')
      if (writerMessages.length > 0) {
        const latestWriterMessage = writerMessages[writerMessages.length - 1]
        setFinalContent(latestWriterMessage.content || '')
      } else {
        setFinalContent('')
      }
    }
  }

  // Handle template formatting for Panel 2
  const handleFormatWithTemplate = async (feedback?: string) => {
    if (!selectedFormat || !selectedConversation) return

    setIsFormatting(true)
    try {
      // Get the latest Writer message as the draft
      const writerMessage = messages.find(msg => msg.agent_name === 'Writer')
      if (!writerMessage) {
        alert('No Writer content found to format')
        return
      }

      const requestBody: any = {
        conversation_id: selectedConversation.id,
        draft: writerMessage.content,
        category: selectedConversation.state?.category,
        format: selectedFormat,
      }

      // Add feedback if provided
      if (feedback && feedback.trim()) {
        requestBody.feedback = feedback.trim()
      }

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/format-agent/transform`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      })

      if (!response.ok) {
        throw new Error('Failed to format content')
      }
      
      // Refresh the messages to show the new formatted content
      await handleConversationSelect(selectedConversation)
      
      // Clear feedback if it was used
      if (feedback) {
        setFeedbackText('')
      }
      
      alert('Content formatted successfully!')
    } catch (error) {
      console.error('Error:', error)
      alert('Failed to format content. Make sure the backend server is running.')
    } finally {
      setIsFormatting(false)
    }
  }

  // Handle feedback submission
  const handleSubmitFeedback = async () => {
    if (!feedbackText.trim()) {
      alert('Please enter feedback before submitting')
      return
    }

    if (!selectedConversation) {
      alert('Please select a conversation first')
      return
    }

    console.log('Submitting feedback:', feedbackText.trim())
    console.log('Selected conversation:', selectedConversation.id)

    setIsSubmittingFeedback(true)
    try {
      // Get the latest Writer message as the draft
      const writerMessage = messages.find(msg => msg.agent_name === 'Writer')
      if (!writerMessage) {
        alert('No Writer content found to provide feedback on')
        return
      }

      console.log('Using draft from message:', writerMessage.id)

      const requestBody = {
        conversation_id: selectedConversation.id,
        draft: writerMessage.content,
        category: selectedConversation.state?.category,
        format: selectedFormat || 'general', // Use 'general' if no format selected
        feedback: feedbackText.trim()
      }

      console.log('Request body:', requestBody)

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/format-agent/transform`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      })

      console.log('Response status:', response.status)

      if (!response.ok) {
        const errorText = await response.text()
        console.error('Error response:', errorText)
        throw new Error(`Failed to submit feedback: ${response.status} ${response.statusText}`)
      }
      
      const result = await response.json()
      console.log('Success response:', result)
      
      // Refresh the messages to show the new formatted content
      await handleConversationSelect(selectedConversation)
      
      // Clear feedback
      setFeedbackText('')
      
      alert('Feedback submitted successfully!')
    } catch (error) {
      console.error('Error submitting feedback:', error)
      alert(`Failed to submit feedback: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setIsSubmittingFeedback(false)
    }
  }

  // Handle saving the final post content and status
  const handleSavePost = async () => {
    if (!selectedConversation || !finalContent.trim()) {
      alert('Please select a conversation and enter content to save')
      return
    }

    setIsSavingPost(true)
    try {
      // Update the conversation with the final content and status
      const { data, error } = await supabase
        .from('conversations')
        .update({
          status: postStatus,
          state: {
            ...selectedConversation.state,
            final_content: finalContent.trim(),
            user_satisfied: postStatus === 'completed',
            waiting_for_user: postStatus !== 'completed'
          },
          updated_at: new Date().toISOString()
        })
        .eq('id', selectedConversation.id)
        .select()

      console.log('Update result:', { data, error })

      if (error) {
        console.error('Supabase update error details:', error)
        throw new Error(`Database update failed: ${error.message}`)
      }

      if (!data || data.length === 0) {
        throw new Error('No rows were updated - conversation might not exist')
      }

      // Also add a message to record the final content
      const { data: messageData, error: messageError } = await supabase
        .from('messages')
        .insert({
          conversation_id: selectedConversation.id,
          role: 'user',
          content: `Final post content saved with status: ${postStatus}`,
          agent_name: 'Final Editor',
          metadata: {
            final_content: finalContent.trim(),
            status: postStatus
          }
        })
        .select()

      console.log('Message insert result:', { messageData, messageError })

      if (messageError) {
        console.error('Failed to add final message:', messageError)
        // Don't throw here - the main update succeeded, this is just a log
      }

      // Refresh conversations list
      await fetchConversations()
      
      alert('Post saved successfully!')
    } catch (error) {
      console.error('Error saving post:', error)
      alert(`Failed to save post: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setIsSavingPost(false)
    }
  }

  // Helper function to fetch conversations (extracted for reuse)
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
      setError('Failed to load conversations.')
    } finally {
      setIsLoading(false)
    }
  }

  // Dynamic panel width calculations based on all panel states
  const calculatePanelWidths = () => {
    const modes = [panel1Mode, panel2Mode, panel3Mode]
    const closedCount = modes.filter(m => m === 'closed').length
    const defaultCount = modes.filter(m => m === 'default').length
    const expandedCount = modes.filter(m => m === 'expanded').length
    
    // Base weights for each mode (closed=5%, default=20%, expanded=50%)
    const weights = {
      closed: 1,    // 5%
      default: 4,   // 20%
      expanded: 10  // 50%
    }
    
    // Calculate total weight
    const totalWeight = closedCount * weights.closed + defaultCount * weights.default + expandedCount * weights.expanded
    
    // Calculate percentage for each mode
    const getWidth = (mode: PanelMode) => {
      const weight = weights[mode]
      const percentage = (weight / totalWeight) * 100
      return percentage.toFixed(1)
    }
    
    return {
      panel1: getWidth(panel1Mode),
      panel2: getWidth(panel2Mode),
      panel3: getWidth(panel3Mode)
    }
  }

  const panelWidths = calculatePanelWidths()

  return (
    <div className="h-screen w-screen flex bg-background">
      {/* Panel 1: Sources */}
      <div 
        className="border-r border-border bg-card transition-all duration-300 flex flex-col"
        style={{ width: `${panelWidths.panel1}%` }}
      >
        {isAddingPost ? (
          // Add Post Mode - Expanded form
          <>
            <div className="p-4 border-b border-border flex items-center justify-between">
              <h2 className="text-lg font-semibold text-card-foreground">Create New Post</h2>
              <Button 
                onClick={handleCancelAddPost}
                variant="outline"
                size="sm"
              >
                Cancel
              </Button>
            </div>
            
            <div className="flex-1 overflow-y-auto p-4">
              <Card>
                <CardContent className="p-4 space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-card-foreground mb-2">
                      Post Title
                    </label>
                    <Input
                      value={newPostTitle}
                      onChange={(e) => setNewPostTitle(e.target.value)}
                      placeholder="Enter post title..."
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-card-foreground mb-2">
                      Content
                    </label>
                    <Textarea
                      rows={8}
                      value={newPostContent}
                      onChange={(e) => setNewPostContent(e.target.value)}
                      placeholder="Write your post content here..."
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-card-foreground mb-2">
                      Tags (optional)
                    </label>
                    <Input
                      value={newPostTags}
                      onChange={(e) => setNewPostTags(e.target.value)}
                      placeholder="e.g., linkedin, networking, ai (comma separated)"
                    />
                  </div>
                  
                  <div className="flex space-x-2">
                    <Button 
                      onClick={handleCreatePost}
                      disabled={isCreatingPost}
                      className="flex-1"
                    >
                      {isCreatingPost ? 'Creating...' : 'Create Post'}
                    </Button>
                    <Button 
                      onClick={handleCancelAddPost}
                      disabled={isCreatingPost}
                      variant="outline"
                    >
                      Cancel
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          </>
        ) : (
          // Default Mode - Posts List
          <>
            <div className="p-4 border-b border-border flex items-center justify-between">
              <h2 className="text-lg font-semibold text-card-foreground">Posts</h2>
              <div className="flex items-center gap-2">
                <Button 
                  onClick={handleAddPost}
                  size="sm"
                >
                  + Add
                </Button>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPanel1Mode(panel1Mode === 'closed' ? 'default' : 'closed')}
                    className="p-3 hover:bg-muted rounded transition-colors text-2xl font-bold"
                    title={panel1Mode === 'closed' ? 'Expand' : 'Collapse'}
                  >
                    {panel1Mode === 'closed' ? '□' : '⊡'}
                  </button>
                  <button
                    onClick={() => setPanel1Mode('expanded')}
                    className="p-3 hover:bg-muted rounded transition-colors text-2xl"
                    title="Maximize"
                  >
                    ⤢
                  </button>
                </div>
              </div>
            </div>
            
            <div className="flex-1 overflow-y-auto">
              {isLoading ? (
                <div className="p-4 text-center text-muted-foreground text-sm">
                  Loading posts...
                </div>
              ) : error ? (
                <div className="p-4 text-center text-destructive text-sm">
                  {error}
                </div>
              ) : conversations.length === 0 ? (
                <div className="p-4 text-center text-muted-foreground text-sm">
                  No posts yet.<br />
                  <Button 
                    onClick={handleAddPost}
                    variant="link"
                    className="text-xs p-0 h-auto"
                  >
                    Create your first post
                  </Button>
                </div>
              ) : (
                <div className="divide-y divide-border">
                  {conversations.map((conversation) => (
                    <div 
                      key={conversation.id} 
                      className={`p-3 hover:bg-accent cursor-pointer transition-colors ${
                        selectedConversation?.id === conversation.id ? 'bg-accent border-l-2 border-primary' : ''
                      }`}
                      onClick={() => handleConversationSelect(conversation)}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <h3 className="text-sm font-medium text-card-foreground truncate flex-1">
                          {conversation.title}
                        </h3>
                        {getStatusBadge(conversation.status, conversation.state)}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {new Date(conversation.updated_at).toLocaleDateString()}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
        
      </div>

      {/* Panel 2: Chat */}
      <div 
        className="border-r border-border bg-muted/30 transition-all duration-300 flex flex-col"
        style={{ width: `${panelWidths.panel2}%` }}
      >
        <div className="p-4 border-b border-border flex items-center justify-between">
          <h2 className="text-lg font-semibold text-card-foreground">Chat</h2>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPanel2Mode(panel2Mode === 'closed' ? 'default' : 'closed')}
              className="p-3 hover:bg-muted rounded transition-colors text-2xl font-bold"
              title={panel2Mode === 'closed' ? 'Expand' : 'Collapse'}
            >
              {panel2Mode === 'closed' ? '□' : '⊡'}
            </button>
            <button
              onClick={() => setPanel2Mode('expanded')}
              className="p-3 hover:bg-muted rounded transition-colors text-2xl"
              title="Maximize"
            >
              ⤢
            </button>
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto">
          {selectedConversation ? (
            <div className="h-full flex flex-col">
              {/* Conversation Header */}
              <div className="p-4 bg-card border-b border-border">
                <h3 className="text-sm font-medium text-card-foreground truncate">
                  {selectedConversation.title}
                </h3>
                <div className="text-xs text-muted-foreground mt-1">
                  {new Date(selectedConversation.updated_at).toLocaleDateString()}
                </div>
              </div>
              
              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4">
                {isLoadingMessages ? (
                  <div className="text-center text-muted-foreground text-sm">
                    Loading messages...
                  </div>
                ) : messages.length === 0 ? (
                  <div className="text-center text-muted-foreground text-sm">
                    No messages yet
                  </div>
                ) : (
                  <div className="space-y-3">
                    {messages.map((message) => (
                      <Card key={message.id} className="p-4">
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-2">
                            <Badge variant={
                              message.role === 'user' ? 'default' :
                              message.role === 'assistant' ? 'secondary' :
                              'outline'
                            }>
                              {message.role}
                            </Badge>
                            {message.agent_name && (
                              <Badge variant="outline" className="border-purple-500 text-purple-500">
                                {message.agent_name}
                              </Badge>
                            )}
                          </div>
                          <span className="text-xs text-muted-foreground">
                            {new Date(message.created_at).toLocaleTimeString()}
                          </span>
                        </div>
                        <div className="text-sm text-card-foreground whitespace-pre-wrap">
                          {message.content}
                        </div>
                      </Card>
                    ))}
                  </div>
                )}
              </div>
              
              {/* Tab Bar at Bottom */}
              {messages.some(msg => msg.agent_name === 'Writer') && (
                <div className="border-t border-border bg-muted/50">
                  {/* Tab Buttons */}
                  <div className="flex">
                    <button
                      onClick={() => setShowFeedbackTab(!showFeedbackTab)}
                      className={`flex-1 px-3 py-2 text-xs font-medium transition-colors ${
                        showFeedbackTab 
                          ? 'bg-primary text-primary-foreground' 
                          : 'bg-muted/30 text-muted-foreground hover:bg-muted/50'
                      }`}
                    >
                      💬 Feedback
                    </button>
                    <button
                      onClick={() => setShowTemplateTab(!showTemplateTab)}
                      className={`flex-1 px-3 py-2 text-xs font-medium transition-colors ${
                        showTemplateTab 
                          ? 'bg-primary text-primary-foreground' 
                          : 'bg-muted/30 text-muted-foreground hover:bg-muted/50'
                      }`}
                    >
                      🎨 Re-format
                    </button>
                  </div>

                  {/* Feedback Tab Content */}
                  {showFeedbackTab && (
                    <div className="p-3 border-t border-border bg-card">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium">💬 Give Feedback</span>
                        <Button
                          onClick={() => setShowFeedbackTab(false)}
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0"
                        >
                          ✕
                        </Button>
                      </div>
                      <div className="flex gap-2">
                        <Textarea
                          value={feedbackText}
                          onChange={(e) => setFeedbackText(e.target.value)}
                          placeholder="Add feedback to improve the format..."
                          className="flex-1 text-sm resize-none"
                          disabled={isSubmittingFeedback || isFormatting}
                        />
                        <Button
                          onClick={handleSubmitFeedback}
                          disabled={!feedbackText.trim() || isSubmittingFeedback || isFormatting}
                          size="sm"
                          className="text-sm bg-green-600 hover:bg-green-700"
                        >
                          {isSubmittingFeedback ? 'Sending...' : 'Send'}
                        </Button>
                      </div>
                    </div>
                  )}

                  {/* Template Tab Content */}
                  {showTemplateTab && (
                    <div className="p-3 border-t border-border bg-card">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium">🎨 Re-format Content</span>
                        <Button
                          onClick={() => setShowTemplateTab(false)}
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0"
                        >
                          ✕
                        </Button>
                      </div>
                      <div className="flex gap-2">
                        <Select
                          value={selectedFormat}
                          onValueChange={setSelectedFormat}
                          disabled={isFormatting || isSubmittingFeedback}
                        >
                          <SelectTrigger className="text-sm flex-1">
                            <SelectValue placeholder="Select format..." />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="belief_shift">Belief Shift</SelectItem>
                            <SelectItem value="origin_story">Origin Story</SelectItem>
                            <SelectItem value="industry_myths">Industry Myths</SelectItem>
                            <SelectItem value="framework">Framework</SelectItem>
                            <SelectItem value="step_by_step">Step-by-step</SelectItem>
                            <SelectItem value="how_i_how_to">How I / How to</SelectItem>
                            <SelectItem value="objection_post">Objection Post</SelectItem>
                            <SelectItem value="result_breakdown">Result Breakdown</SelectItem>
                            <SelectItem value="client_success_story">Client Success Story</SelectItem>
                          </SelectContent>
                        </Select>
                        <Button
                          onClick={() => handleFormatWithTemplate()}
                          disabled={!selectedFormat || isFormatting || isSubmittingFeedback}
                          size="sm"
                          className="text-sm"
                        >
                          {isFormatting ? 'Formatting...' : 'Format'}
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="p-4 text-center text-muted-foreground text-sm">
              Select a conversation from the left to view chat details
            </div>
          )}
        </div>
        
      </div>

            {/* Panel 3: Writing */}
            <div 
              className="bg-card transition-all duration-300 flex flex-col"
              style={{ width: `${panelWidths.panel3}%` }}
            >
              <div className="p-4 border-b border-border flex items-center justify-between">
                <h2 className="text-lg font-semibold text-card-foreground">Writing</h2>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPanel3Mode(panel3Mode === 'closed' ? 'default' : 'closed')}
                    className="p-3 hover:bg-muted rounded transition-colors text-2xl font-bold"
                    title={panel3Mode === 'closed' ? 'Expand' : 'Collapse'}
                  >
                    {panel3Mode === 'closed' ? '□' : '⊡'}
                  </button>
                  <button
                    onClick={() => setPanel3Mode('expanded')}
                    className="p-3 hover:bg-muted rounded transition-colors text-2xl"
                    title="Maximize"
                  >
                    ⤢
                  </button>
                </div>
              </div>
              
              <div className="flex-1 overflow-y-auto p-4">
                {selectedConversation ? (
                  <div className="h-full flex flex-col space-y-3">
                    {/* Status Management - Compact */}
                    <div className="flex items-center gap-2 p-2 bg-muted/20 border border-border/30 rounded-md">
                      <span className="text-xs font-medium text-muted-foreground">Status:</span>
                      <Select
                        value={postStatus}
                        onValueChange={setPostStatus}
                      >
                        <SelectTrigger className="h-6 text-xs w-32">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="active">🔄 Active</SelectItem>
                          <SelectItem value="archived">📦 Archived</SelectItem>
                        </SelectContent>
                      </Select>
                      <div className="flex-1"></div>
                      <span className="text-xs text-muted-foreground">{finalContent.length} chars</span>
                    </div>
                    
                    {/* Content Editor - Full Height */}
                    <div className="flex-1 flex flex-col">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-xs font-medium text-muted-foreground">📝 Content</span>
                        <div className="flex-1 h-px bg-border/30"></div>
                      </div>
                      <Textarea
                        value={finalContent}
                        onChange={(e) => setFinalContent(e.target.value)}
                        placeholder="Edit your final post content here..."
                        className="flex-1 resize-none"
                        disabled={isSavingPost}
                      />
                    </div>
                    
                    {/* Action Buttons - Compact */}
                    <div className="flex gap-2">
                      <Button
                        onClick={handleSavePost}
                        disabled={!finalContent.trim() || isSavingPost}
                        size="sm"
                        className="flex-1"
                      >
                        {isSavingPost ? 'Saving...' : 'Save'}
                      </Button>
                      <Button
                        onClick={() => loadLatestFormattedContent(messages)}
                        disabled={isSavingPost}
                        variant="outline"
                        size="sm"
                      >
                        Reset
                      </Button>
          </div>
        </div>
                ) : (
                  <div className="h-full flex items-center justify-center text-muted-foreground text-sm">
                    Select a conversation from Panel 1 to start writing
                  </div>
                )}
              </div>
              
      </div>
    </div>
  )
}