'use client'

import { useState, useEffect, useCallback } from 'react'
import { supabase } from '@/lib/supabase'

// Define proper interfaces for our data structures
interface Conversation {
  id: string
  title: string
  status: string
  created_at: string
  updated_at: string
  state?: Record<string, unknown> | null
}

interface Message {
  id: string
  role: string
  content: string
  agent_name?: string
  metadata?: Record<string, unknown>
  created_at: string
}

interface Template {
  id: string
  title: string
  content: string
  author?: string
  category: string
  format: string
}
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'

type PanelMode = 'closed' | 'default' | 'expanded'

const CATEGORIES = [
  { value: 'attract', label: 'Attract', description: 'Build awareness and trust' },
  { value: 'nurture', label: 'Nurture', description: 'Show authority/create demand' },
  { value: 'convert', label: 'Convert', description: 'Qualify and filter buyers' }
]

const FORMATS = {
  attract: [
    { value: 'belief_shift', label: 'Belief Shift' },
    { value: 'origin_story', label: 'Origin Story' },
    { value: 'industry_myths', label: 'Industry Myths' }
  ],
  nurture: [
    { value: 'framework', label: 'Framework' },
    { value: 'step_by_step', label: 'Step-by-step' },
    { value: 'how_i_how_to', label: 'How I / How to' }
  ],
  convert: [
    { value: 'objection_post', label: 'Objection Post' },
    { value: 'result_breakdown', label: 'Result Breakdown' },
    { value: 'client_success_story', label: 'Client Success Story' }
  ]
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
  const [isAddingTemplate, setIsAddingTemplate] = useState(false)
  const [newPostTitle, setNewPostTitle] = useState('')
  const [newPostContent, setNewPostContent] = useState('')
  const [newPostTags, setNewPostTags] = useState('')
  const [isCreatingPost, setIsCreatingPost] = useState(false)
  const [newTemplateTitle, setNewTemplateTitle] = useState('')
  const [newTemplateContent, setNewTemplateContent] = useState('')
  const [newTemplateAuthor, setNewTemplateAuthor] = useState('')
  const [newTemplateLinkedinUrl, setNewTemplateLinkedinUrl] = useState('')
  const [newTemplateCategory, setNewTemplateCategory] = useState('attract')
  const [newTemplateFormat, setNewTemplateFormat] = useState('belief_shift')
  const [newTemplateTags, setNewTemplateTags] = useState('')
  const [newTemplateScreenshotUrl, setNewTemplateScreenshotUrl] = useState('')
  const [isCreatingTemplate, setIsCreatingTemplate] = useState(false)
  
  // Panel 2: Chat state
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoadingMessages, setIsLoadingMessages] = useState(false)
  const [selectedFormat, setSelectedFormat] = useState('')
  const [isFormatting, setIsFormatting] = useState(false)
  const [feedbackText, setFeedbackText] = useState('')
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false)
  const [showFeedbackTab, setShowFeedbackTab] = useState(false)
  const [showTemplateTab, setShowTemplateTab] = useState(false)
  const [showFeedbackHistory, setShowFeedbackHistory] = useState(false)
  
  // Panel 2 tabs state
  const [panel2ActiveTab, setPanel2ActiveTab] = useState<'content' | 'templates'>('content')
  
  // Template browsing state
  const [templates, setTemplates] = useState<Template[]>([])
  const [filteredTemplates, setFilteredTemplates] = useState<Template[]>([])
  const [currentTemplateIndex, setCurrentTemplateIndex] = useState(0)
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(false)
  const [templateFilters, setTemplateFilters] = useState({
    category: '',
    format: '',
    author: ''
  })
  
  // Panel 3: Writing state
  const [finalContent, setFinalContent] = useState('')
  const [postStatus, setPostStatus] = useState('')
  const [isSavingPost, setIsSavingPost] = useState(false)
  
  // Post editing state
  const [editingPostId, setEditingPostId] = useState<string | null>(null)
  const [editingPostTitle, setEditingPostTitle] = useState('')
  const [isUpdatingPost, setIsUpdatingPost] = useState(false)

  // Fetch conversations on component mount
  useEffect(() => {
    fetchConversations()
  }, [])

  // Filter templates based on current filters
  const applyFilters = useCallback(() => {
    const filtered = templates.filter(template => {
      // Handle "all" values and empty strings
      if (templateFilters.category && templateFilters.category !== 'all' && template.category !== templateFilters.category) return false
      if (templateFilters.format && templateFilters.format !== 'all' && template.format !== templateFilters.format) return false
      if (templateFilters.author && templateFilters.author !== 'all' && !template.author?.toLowerCase().includes(templateFilters.author.toLowerCase())) return false
      return true
    })
    console.log('Filtering templates:', { 
      totalTemplates: templates.length, 
      filters: templateFilters, 
      filteredCount: filtered.length 
    })
    setFilteredTemplates(filtered)
    setCurrentTemplateIndex(0) // Reset to first template when filters change
  }, [templates, templateFilters])

  // Apply filters when they change
  useEffect(() => {
    applyFilters()
  }, [applyFilters])

  // Helper function for status badges
  const getStatusBadge = (status: string, state?: Record<string, unknown> | null) => {
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
    setIsAddingTemplate(false)
    setPanel1Mode('default')
    // Reset post form fields
    setNewPostTitle('')
    setNewPostContent('')
    setNewPostTags('')
    // Reset template form fields
    setNewTemplateTitle('')
    setNewTemplateContent('')
    setNewTemplateAuthor('')
    setNewTemplateLinkedinUrl('')
    setNewTemplateCategory('attract')
    setNewTemplateFormat('belief_shift')
    setNewTemplateTags('')
    setNewTemplateScreenshotUrl('')
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

  const handleCreateTemplate = async () => {
    if (!newTemplateTitle.trim() || !newTemplateContent.trim()) {
      alert('Please fill in both title and content')
      return
    }

    setIsCreatingTemplate(true)
    try {
      // Use the backend API to create a template
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/templates`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: newTemplateTitle.trim(),
          content: newTemplateContent.trim(),
          category: newTemplateCategory,
          format: newTemplateFormat,
          author: newTemplateAuthor.trim() || null,
          linkedin_url: newTemplateLinkedinUrl.trim() || null,
          tags: newTemplateTags.split(',').map(tag => tag.trim()).filter(tag => tag),
          screenshot_url: newTemplateScreenshotUrl.trim() || null
        }),
      })

      if (!response.ok) {
        throw new Error(`Failed to create template: ${response.status} ${response.statusText}`)
      }

      const result = await response.json()
      console.log('Template created successfully:', result)

      // Reset form and return to default mode
      setNewTemplateTitle('')
      setNewTemplateContent('')
      setNewTemplateAuthor('')
      setNewTemplateLinkedinUrl('')
      setNewTemplateCategory('attract')
      setNewTemplateFormat('belief_shift')
      setNewTemplateTags('')
      setNewTemplateScreenshotUrl('')
      setIsAddingTemplate(false)
      setPanel1Mode('default')
      
      alert('Template created successfully!')
    } catch (err) {
      console.error('Error creating template:', err)
      alert(`Failed to create template: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setIsCreatingTemplate(false)
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
      loadLatestFormattedContent(data || [], conversation)
      
      // Set the current post status
      setPostStatus(conversation.status || 'draft')
    } catch (err) {
      console.error('Error fetching messages:', err)
      setMessages([])
    } finally {
      setIsLoadingMessages(false)
    }
  }

  // Get feedback messages from the conversation
  const getFeedbackMessages = (messages: Message[]) => {
    return messages.filter(msg => 
      msg.agent_name === 'Format Agent' && 
      msg.metadata?.feedback && 
      (msg.metadata.feedback as string).trim() !== ''
    ).map(msg => ({
      content: msg.metadata?.feedback as string,
      timestamp: msg.created_at,
      id: msg.id
    }))
  }

  // Load the latest formatted content for Panel 3
  const loadLatestFormattedContent = (messages: Message[], conversation: Conversation) => {
    // Priority order: Final Editor > Format Agent > Writer
    
    // 1. Check for Final Editor message (user's saved version) - highest priority
    const finalEditorMessages = messages.filter(msg => msg.agent_name === 'Final Editor')
    if (finalEditorMessages.length > 0) {
      const latestFinalEditorMessage = finalEditorMessages[finalEditorMessages.length - 1]
      
      // Check if the message contains actual content or just a status message
      const content = latestFinalEditorMessage.content || ''
      
      // If it's just a status message, try to get the actual content from the message metadata
      if (content.includes('Final post content saved with status:')) {
        // Try to get the actual content from the conversation state
        if (conversation.state?.final_content) {
          setFinalContent(conversation.state.final_content as string)
          return
        }
        // If no state content, skip to next priority
      } else {
        // This is actual content, use it
        setFinalContent(content)
        return
      }
    }
    
    // 2. Check for saved content in conversation state - second priority
    if (conversation.state?.final_content) {
      setFinalContent(conversation.state.final_content as string)
      return
    }
    
    // 3. Check for Format Agent message (AI formatted content) - third priority
    const formatAgentMessages = messages.filter(msg => msg.agent_name === 'Format Agent')
    if (formatAgentMessages.length > 0) {
      const latestFormatMessage = formatAgentMessages[formatAgentMessages.length - 1]
      setFinalContent(latestFormatMessage.content || '')
      return
    }

    // 4. Fallback to Writer message (initial draft) - lowest priority
    const writerMessages = messages.filter(msg => msg.agent_name === 'Writer')
    if (writerMessages.length > 0) {
      const latestWriterMessage = writerMessages[writerMessages.length - 1]
      setFinalContent(latestWriterMessage.content || '')
      return
    }
    
    // 5. No content found
    setFinalContent('')
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

      const requestBody: Record<string, unknown> = {
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
      console.log('API URL:', process.env.NEXT_PUBLIC_API_URL)

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      console.log('Using API URL:', apiUrl)

      const response = await fetch(`${apiUrl}/format-agent/transform`, {
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
      
      // Handle different types of errors
      if (error instanceof TypeError && error.message === 'Failed to fetch') {
        alert('Network error: Could not connect to the server. Please check your internet connection and try again.')
      } else {
        alert(`Failed to submit feedback: ${error instanceof Error ? error.message : 'Unknown error'}`)
      }
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
          content: finalContent.trim(), // Store the actual content, not a status message
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

  // Helper function to fetch templates
  const fetchTemplates = useCallback(async () => {
    setIsLoadingTemplates(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL
      console.log('Fetching templates from:', `${apiUrl}/templates`)
      
      const response = await fetch(`${apiUrl}/templates`)
      console.log('Templates response status:', response.status)
      
      if (!response.ok) {
        const errorText = await response.text()
        console.error('Templates response error:', errorText)
        throw new Error(`Failed to fetch templates: ${response.status} ${response.statusText}`)
      }
      
      const data = await response.json()
      console.log('Templates data:', data)
      const templatesList = data.templates || []
      console.log('Templates list length:', templatesList.length)
      
      // If no templates exist, create some sample templates for testing
      if (templatesList.length === 0) {
        console.log('No templates found, creating sample templates')
        const sampleTemplates = [
          {
            id: 'sample-1',
            title: 'Industry Insight Post',
            content: 'The insurance industry is at a crossroads. With climate change accelerating and cyber threats evolving, traditional risk models are becoming obsolete.\n\nHere\'s what we\'re seeing:\n• Claims costs up 15% YoY\n• New risk categories emerging\n• AI changing the game\n\nWhat trends are you seeing in your sector?',
            author: 'Industry Expert',
            category: 'attract',
            format: 'industry_myths'
          },
          {
            id: 'sample-2', 
            title: 'Framework for Success',
            content: 'After 10 years in data transformation, I\'ve learned that success comes down to 3 key pillars:\n\n1. **People First** - Technology means nothing without buy-in\n2. **Incremental Wins** - Small victories build momentum\n3. **Data Quality** - Garbage in, garbage out\n\nWhat framework works for your team?',
            author: 'Data Leader',
            category: 'nurture',
            format: 'framework'
          },
          {
            id: 'sample-3',
            title: 'Client Success Story',
            content: 'Just wrapped up a 6-month data transformation project with a mid-size insurer.\n\n**The Challenge:** Scattered data across 12 systems\n**The Solution:** Unified data platform + change management\n**The Result:** 40% faster reporting, 60% reduction in manual work\n\nSometimes the biggest wins come from the simplest solutions. What\'s your biggest transformation win?',
            author: 'Consultant',
            category: 'convert',
            format: 'client_success_story'
          }
        ]
        setTemplates(sampleTemplates)
        setFilteredTemplates(sampleTemplates)
      } else {
        setTemplates(templatesList)
        setFilteredTemplates(templatesList)
      }
      setCurrentTemplateIndex(0)
    } catch (err) {
      console.error('Error fetching templates:', err)
      // Even on error, show sample templates so the feature works
      const fallbackTemplates = [
        {
          id: 'fallback-1',
          title: 'Sample Post Template',
          content: 'This is a sample template to demonstrate the template viewer functionality.\n\nYou can navigate between templates using the arrow buttons and see the full content flow.',
          author: 'System',
          category: 'attract',
          format: 'belief_shift'
        }
      ]
      setTemplates(fallbackTemplates)
      setFilteredTemplates(fallbackTemplates)
      setCurrentTemplateIndex(0)
    } finally {
      setIsLoadingTemplates(false)
    }
  }, [])

  // Navigate to previous template
  const goToPreviousTemplate = () => {
    setCurrentTemplateIndex(prev => 
      prev > 0 ? prev - 1 : filteredTemplates.length - 1
    )
  }

  // Navigate to next template
  const goToNextTemplate = () => {
    setCurrentTemplateIndex(prev => 
      prev < filteredTemplates.length - 1 ? prev + 1 : 0
    )
  }

  // Start editing a post title
  const startEditingPost = (post: Conversation) => {
    setEditingPostId(post.id)
    setEditingPostTitle(post.title)
  }

  // Cancel editing
  const cancelEditingPost = () => {
    setEditingPostId(null)
    setEditingPostTitle('')
  }

  // Save post title changes
  const savePostTitle = async () => {
    if (!editingPostId || !editingPostTitle.trim()) return

    setIsUpdatingPost(true)
    try {
      const { error } = await supabase
        .from('conversations')
        .update({ title: editingPostTitle.trim() })
        .eq('id', editingPostId)

      if (error) {
        console.error('Error updating post title:', error)
        alert(`Error updating post title: ${error.message}`)
        return
      }

      // Update the conversations list
      setConversations(prev => 
        prev.map(conv => 
          conv.id === editingPostId 
            ? { ...conv, title: editingPostTitle.trim() }
            : conv
        )
      )

      // Update selected conversation if it's the one being edited
      if (selectedConversation?.id === editingPostId) {
        setSelectedConversation(prev => 
          prev ? { ...prev, title: editingPostTitle.trim() } : null
        )
      }

      setEditingPostId(null)
      setEditingPostTitle('')
    } catch (err) {
      console.error('Error updating post title:', err)
      alert(`Error updating post title: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setIsUpdatingPost(false)
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
        {(isAddingPost || isAddingTemplate) ? (
          // Add Mode - Expanded form
          <>
            <div className="p-4 border-b border-border flex items-center justify-between">
              <h2 className="text-lg font-semibold text-card-foreground">
                {isAddingPost ? 'Create New Post' : 'Create New Template'}
              </h2>
              <Button 
                onClick={() => {
                  setIsAddingPost(false)
                  setIsAddingTemplate(false)
                  setPanel1Mode('default')
                }}
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
                      {isAddingPost ? 'Post Title' : 'Template Title'}
                    </label>
                    <Input
                      value={isAddingPost ? newPostTitle : newTemplateTitle}
                      onChange={(e) => isAddingPost ? setNewPostTitle(e.target.value) : setNewTemplateTitle(e.target.value)}
                      placeholder={isAddingPost ? 'Enter post title...' : 'Enter template title...'}
                      disabled={isCreatingPost || isCreatingTemplate}
                    />
        </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-card-foreground mb-2">
                      Content
                    </label>
                    <Textarea
                      rows={8}
                      value={isAddingPost ? newPostContent : newTemplateContent}
                      onChange={(e) => isAddingPost ? setNewPostContent(e.target.value) : setNewTemplateContent(e.target.value)}
                      placeholder={isAddingPost ? 'Write your post content here...' : 'Write your template content here...'}
                      disabled={isCreatingPost || isCreatingTemplate}
                    />
      </div>
                  
                  {isAddingPost && (
                    <div>
                      <label className="block text-sm font-medium text-card-foreground mb-2">
                        Tags (optional)
                      </label>
                      <Input
                        value={newPostTags}
                        onChange={(e) => setNewPostTags(e.target.value)}
                        placeholder="e.g., linkedin, networking, ai (comma separated)"
                        disabled={isCreatingPost}
                      />
                    </div>
                  )}

                  {isAddingTemplate && (
                    <>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium text-card-foreground mb-2">
                            Author
                          </label>
                          <Input
                            value={newTemplateAuthor}
                            onChange={(e) => setNewTemplateAuthor(e.target.value)}
                            placeholder="Author name"
                            disabled={isCreatingTemplate}
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-card-foreground mb-2">
                            LinkedIn URL
                          </label>
                          <Input
                            value={newTemplateLinkedinUrl}
                            onChange={(e) => setNewTemplateLinkedinUrl(e.target.value)}
                            placeholder="https://linkedin.com/in/..."
                            disabled={isCreatingTemplate}
                          />
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium text-card-foreground mb-2">
                            Category
                          </label>
                          <Select
                            value={newTemplateCategory}
                            onValueChange={(value) => {
                              setNewTemplateCategory(value)
                              // Reset format when category changes
                              const categoryFormats = FORMATS[value as keyof typeof FORMATS]
                              if (categoryFormats && categoryFormats.length > 0) {
                                setNewTemplateFormat(categoryFormats[0].value)
                              }
                            }}
                            disabled={isCreatingTemplate}
                          >
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {CATEGORIES.map((category) => (
                                <SelectItem key={category.value} value={category.value}>
                                  {category.label} - {category.description}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-card-foreground mb-2">
                            Format
                          </label>
                          <Select
                            value={newTemplateFormat}
                            onValueChange={setNewTemplateFormat}
                            disabled={isCreatingTemplate}
                          >
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {FORMATS[newTemplateCategory as keyof typeof FORMATS]?.map((format) => (
                                <SelectItem key={format.value} value={format.value}>
                                  {format.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-card-foreground mb-2">
                          Tags (comma-separated)
                        </label>
                        <Input
                          value={newTemplateTags}
                          onChange={(e) => setNewTemplateTags(e.target.value)}
                          placeholder="e.g., linkedin, networking, ai"
                          disabled={isCreatingTemplate}
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-card-foreground mb-2">
                          Screenshot URL (optional)
                        </label>
                        <Input
                          value={newTemplateScreenshotUrl}
                          onChange={(e) => setNewTemplateScreenshotUrl(e.target.value)}
                          placeholder="https://example.com/screenshot.png"
                          disabled={isCreatingTemplate}
                        />
                      </div>
                    </>
                  )}
                  
                  <div className="flex space-x-2">
                    <Button 
                      onClick={isAddingPost ? handleCreatePost : handleCreateTemplate}
                      disabled={
                        (isAddingPost && isCreatingPost) || 
                        (isAddingTemplate && isCreatingTemplate)
                      }
                      className="flex-1"
                    >
                      {isCreatingPost ? 'Creating...' : isCreatingTemplate ? 'Creating...' : 
                       isAddingPost ? 'Create Post' : 'Create Template'}
                    </Button>
                    <Button 
                      onClick={() => {
                        setIsAddingPost(false)
                        setIsAddingTemplate(false)
                        setPanel1Mode('default')
                      }}
                      disabled={isCreatingPost || isCreatingTemplate}
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
            <div className="border-b border-border">
              {/* Header with Panel Controls */}
              <div className="p-4 flex items-center justify-between">
                <h2 className="text-lg font-semibold text-card-foreground">Posts</h2>
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
              
              {/* Tab System */}
              <div className="flex">
                <button
                  onClick={() => {
                    setIsAddingPost(true)
                    setIsAddingTemplate(false)
                    setPanel1Mode('expanded')
                  }}
                  className={`flex-1 px-3 py-2 text-sm font-medium transition-colors ${
                    isAddingPost 
                      ? 'bg-primary text-primary-foreground' 
                      : 'bg-muted/30 text-muted-foreground hover:bg-muted/50'
                  }`}
                >
                  + Add Post
                </button>
                <button
                  onClick={() => {
                    setIsAddingTemplate(true)
                    setIsAddingPost(false)
                    setPanel1Mode('expanded')
                  }}
                  className={`flex-1 px-3 py-2 text-sm font-medium transition-colors ${
                    isAddingTemplate 
                      ? 'bg-primary text-primary-foreground' 
                      : 'bg-muted/30 text-muted-foreground hover:bg-muted/50'
                  }`}
                >
                  + Add Template
                </button>
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
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex-1 min-w-0">
                          {editingPostId === conversation.id ? (
                            <div className="flex items-center gap-2">
                              <Input
                                value={editingPostTitle}
                                onChange={(e) => setEditingPostTitle(e.target.value)}
                                className="h-7 text-sm"
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter') {
                                    savePostTitle()
                                  } else if (e.key === 'Escape') {
                                    cancelEditingPost()
                                  }
                                }}
                                autoFocus
                              />
                              <Button
                                onClick={savePostTitle}
                                size="sm"
                                className="h-7 px-2"
                                disabled={isUpdatingPost}
                              >
                                ✓
                              </Button>
                              <Button
                                onClick={cancelEditingPost}
                                size="sm"
                                variant="outline"
                                className="h-7 px-2"
                                disabled={isUpdatingPost}
                              >
                                ✕
                              </Button>
                            </div>
                          ) : (
                            <h3 
                              className="text-sm font-medium text-card-foreground truncate hover:text-primary cursor-pointer"
                              onClick={(e) => {
                                e.stopPropagation()
                                startEditingPost(conversation)
                              }}
                              title="Click to rename"
                            >
                              {conversation.title}
                            </h3>
                          )}
                        </div>
                        {getStatusBadge(conversation.status, conversation.state)}
                      </div>
                      <div 
                        className="text-xs text-muted-foreground cursor-pointer"
                        onClick={() => handleConversationSelect(conversation)}
                      >
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
        <div className="border-b border-border">
          {/* Header with Panel Controls */}
          <div className="p-4 flex items-center justify-between">
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
          
          {/* Tab System */}
          <div className="flex">
            <button
              onClick={() => setPanel2ActiveTab('content')}
              className={`flex-1 px-3 py-2 text-sm font-medium transition-colors ${
                panel2ActiveTab === 'content'
                  ? 'bg-primary text-primary-foreground' 
                  : 'bg-muted/30 text-muted-foreground hover:bg-muted/50'
              }`}
            >
              📝 View Content
            </button>
            <button
              onClick={() => {
                setPanel2ActiveTab('templates')
                fetchTemplates()
              }}
              className={`flex-1 px-3 py-2 text-sm font-medium transition-colors ${
                panel2ActiveTab === 'templates'
                  ? 'bg-primary text-primary-foreground' 
                  : 'bg-muted/30 text-muted-foreground hover:bg-muted/50'
              }`}
            >
              📚 Browse Templates
            </button>
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto">
          {panel2ActiveTab === 'content' ? (
            // Content Tab - Show chat/conversation
            selectedConversation ? (
              <div className="h-full flex flex-col">
              {/* Conversation Header */}
              <div className="p-4 bg-card border-b border-border">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    {editingPostId === selectedConversation.id ? (
                      <div className="flex items-center gap-2">
                        <Input
                          value={editingPostTitle}
                          onChange={(e) => setEditingPostTitle(e.target.value)}
                          className="h-7 text-sm"
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                              savePostTitle()
                            } else if (e.key === 'Escape') {
                              cancelEditingPost()
                            }
                          }}
                          autoFocus
                        />
                        <Button
                          onClick={savePostTitle}
                          size="sm"
                          className="h-7 px-2"
                          disabled={isUpdatingPost}
                        >
                          ✓
                        </Button>
                        <Button
                          onClick={cancelEditingPost}
                          size="sm"
                          variant="outline"
                          className="h-7 px-2"
                          disabled={isUpdatingPost}
                        >
                          ✕
                        </Button>
                      </div>
                    ) : (
                      <h3 
                        className="text-sm font-medium text-card-foreground truncate hover:text-primary cursor-pointer"
                        onClick={() => startEditingPost(selectedConversation)}
                        title="Click to rename"
                      >
                        {selectedConversation.title}
                      </h3>
                    )}
                    <div className="text-xs text-muted-foreground mt-1">
                      {new Date(selectedConversation.updated_at).toLocaleDateString()}
                    </div>
                  </div>
                  {(() => {
                    // Check for URL in conversation state or messages
                    const state = selectedConversation.state || {}
                    const readwiseUrl = state.readwise_url as string | undefined
                    const sourceUrl = state.source_url as string | undefined
                    const url = readwiseUrl || sourceUrl
                    
                    // If no URL in state, check the first user message for a URL
                    if (!url && messages.length > 0) {
                      const firstUserMessage = messages.find(m => m.role === 'user')
                      if (firstUserMessage?.content) {
                        const urlMatch = firstUserMessage.content.match(/https?:\/\/[^\s]+/)
                        if (urlMatch) {
                          return (
                            <Button
                              asChild
                              variant="outline"
                              size="sm"
                              className="ml-3 h-7 text-xs flex-shrink-0"
                            >
                              <a 
                                href={urlMatch[0]} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                className="flex items-center gap-1"
                              >
                                🔗 Open Source
                              </a>
                            </Button>
                          )
                        }
                      }
                    }
                    
                    // Show button if URL exists in state
                    if (url) {
                      return (
                        <Button
                          asChild
                          variant="outline"
                          size="sm"
                          className="ml-3 h-7 text-xs flex-shrink-0"
                        >
                          <a 
                            href={url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="flex items-center gap-1"
                          >
                            🔗 Open Source
                          </a>
                        </Button>
                      )
                    }
                    
                    return null
                  })()}
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

              {/* Feedback History Section */}
              {getFeedbackMessages(messages).length > 0 && (
                <div className="border-t border-border/50">
                  <div 
                    className="flex items-center justify-between p-3 cursor-pointer hover:bg-muted/30 transition-colors"
                    onClick={() => setShowFeedbackHistory(!showFeedbackHistory)}
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">💬 Your Feedback History</span>
                      <Badge variant="secondary" className="text-xs">
                        {getFeedbackMessages(messages).length}
                      </Badge>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {showFeedbackHistory ? '▼' : '▶'}
                    </span>
                  </div>
                  
                  {showFeedbackHistory && (
                    <div className="px-3 pb-3 space-y-2 max-h-40 overflow-y-auto">
                      {getFeedbackMessages(messages).reverse().map((feedback, index) => (
                        <div key={feedback.id} className="bg-muted/20 rounded-lg p-3 border border-border/30">
                          <div className="flex items-center gap-2 text-xs text-muted-foreground mb-2">
                            <span>Feedback #{getFeedbackMessages(messages).length - index}</span>
                            <span>•</span>
                            <span>{new Date(feedback.timestamp).toLocaleString()}</span>
                          </div>
                          <div className="text-sm whitespace-pre-wrap bg-background/50 p-2 rounded border border-border/20">
                            {feedback.content}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
              
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
            )
          ) : (
            // Templates Tab - Show template browser
            <div className="h-full flex flex-col">
              {/* Template Filters */}
              <div className="p-4 border-b border-border">
                <div className="space-y-3">
                  <div className="grid grid-cols-3 gap-2">
                    <Select
                      value={templateFilters.category || "all"}
                      onValueChange={(value) => setTemplateFilters(prev => ({ ...prev, category: value === "all" ? "" : value }))}
                    >
                      <SelectTrigger className="text-xs">
                        <SelectValue placeholder="Category" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Categories</SelectItem>
                        {CATEGORIES.map((category) => (
                          <SelectItem key={category.value} value={category.value}>
                            {category.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    
                    <Select
                      value={templateFilters.format || "all"}
                      onValueChange={(value) => setTemplateFilters(prev => ({ ...prev, format: value === "all" ? "" : value }))}
                    >
                      <SelectTrigger className="text-xs">
                        <SelectValue placeholder="Format" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Formats</SelectItem>
                        {templateFilters.category ? (
                          FORMATS[templateFilters.category as keyof typeof FORMATS]?.map((format) => (
                            <SelectItem key={format.value} value={format.value}>
                              {format.label}
                            </SelectItem>
                          ))
                        ) : (
                          Object.values(FORMATS).flat().map((format) => (
                            <SelectItem key={format.value} value={format.value}>
                              {format.label}
                            </SelectItem>
                          ))
                        )}
                      </SelectContent>
                    </Select>
                    
                    <Select
                      value={templateFilters.author || "all"}
                      onValueChange={(value) => setTemplateFilters(prev => ({ ...prev, author: value === "all" ? "" : value }))}
                    >
                      <SelectTrigger className="text-xs">
                        <SelectValue placeholder="Author" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Authors</SelectItem>
                        {Array.from(new Set(templates.map(t => t.author).filter(Boolean))).map((author) => (
                          <SelectItem key={author} value={author as string}>
                            {author}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>
              
              {/* Template Viewer */}
              <div className="flex-1 flex flex-col">
                {isLoadingTemplates ? (
                  <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">
                    Loading templates...
                  </div>
                ) : filteredTemplates.length === 0 ? (
                  <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">
                    No templates found matching your filters
                  </div>
                ) : (
                  <>
                    {/* Template Counter */}
                    <div className="p-3 text-center text-xs text-muted-foreground border-b border-border">
                      Template {currentTemplateIndex + 1} of {filteredTemplates.length}
                    </div>
                    
                    {/* Single Template View */}
                    <div className="flex-1 flex items-center justify-between p-4">
                      {/* Previous Arrow */}
                      <Button
                        onClick={goToPreviousTemplate}
                        variant="outline"
                        size="sm"
                        className="h-8 w-8 p-0"
                        disabled={filteredTemplates.length <= 1}
                      >
                        ←
                      </Button>
                      
                      {/* Template Content */}
                      <div className="flex-1 mx-4">
                        <Card className="max-w-2xl mx-auto">
                          <CardHeader className="pb-3">
                            <div className="flex items-start justify-between mb-2">
                              <div className="flex-1">
                                <h3 className="text-lg font-semibold text-card-foreground mb-2">
                                  {filteredTemplates[currentTemplateIndex]?.title}
                                </h3>
                                <div className="flex items-center gap-2">
                                  <Badge variant="outline" className="text-xs">
                                    {CATEGORIES.find(c => c.value === filteredTemplates[currentTemplateIndex]?.category)?.label || filteredTemplates[currentTemplateIndex]?.category}
                                  </Badge>
                                  <Badge variant="secondary" className="text-xs">
                                    {Object.values(FORMATS).flat().find(f => f.value === filteredTemplates[currentTemplateIndex]?.format)?.label || filteredTemplates[currentTemplateIndex]?.format}
                                  </Badge>
                                  {filteredTemplates[currentTemplateIndex]?.author && (
                                    <span className="text-xs text-muted-foreground">
                                      by {filteredTemplates[currentTemplateIndex].author}
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>
                          </CardHeader>
                          <CardContent className="pt-0">
                            <div className="prose prose-sm max-w-none">
                              <pre className="whitespace-pre-wrap text-sm text-card-foreground font-sans leading-relaxed">
                                {filteredTemplates[currentTemplateIndex]?.content}
                              </pre>
                            </div>
                          </CardContent>
                        </Card>
                      </div>
                      
                      {/* Next Arrow */}
                      <Button
                        onClick={goToNextTemplate}
                        variant="outline"
                        size="sm"
                        className="h-8 w-8 p-0"
                        disabled={filteredTemplates.length <= 1}
                      >
                        →
                      </Button>
                    </div>
                  </>
                )}
              </div>
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
                        onClick={() => selectedConversation && loadLatestFormattedContent(messages, selectedConversation)}
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