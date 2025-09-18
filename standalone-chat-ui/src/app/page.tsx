import Link from 'next/link'

export default function Home() {
  return (
    <div className="px-4 py-6 sm:px-0">
      <div className="border-4 border-dashed border-gray-200 rounded-lg h-96 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">
            Welcome to Standalone Chat
          </h1>
          <p className="text-gray-600 mb-6">
            Multi-agent content generation with conversation memory
          </p>
          <div className="space-x-4">
            <Link
              href="/generate-post"
              className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
            >
              Generate Post
            </Link>
            <Link
              href="/posts"
              className="bg-gray-600 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded"
            >
              My Posts
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}