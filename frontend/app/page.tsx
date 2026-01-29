import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col">
      {/* Hero Section */}
      <section className="flex flex-col items-center justify-center px-6 py-20 bg-gradient-to-b from-blue-50 to-white">
        <h1 className="text-5xl font-bold mb-4 text-gray-900">IRONMIND</h1>
        <p className="text-2xl text-gray-700 mb-6">
          Technical Document Intelligence for Aerospace & Defense
        </p>
        <p className="text-lg text-gray-600 max-w-2xl text-center mb-12">
          AI-powered knowledge extraction and analysis for complex technical documentation.
          Leverage hybrid search, knowledge graphs, and multi-source synthesis for precise answers.
        </p>

        {/* Call-to-action buttons */}
        <div className="flex gap-4 mb-16">
          <Link
            href="/login"
            className="px-8 py-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-semibold text-lg shadow-md"
          >
            Get Started
          </Link>
          <Link
            href="#features"
            className="px-8 py-4 border-2 border-blue-600 text-blue-600 rounded-lg hover:bg-blue-50 font-semibold text-lg"
          >
            Learn More
          </Link>
        </div>

        {/* POC Disclaimer - Yellow Warning Box */}
        <div className="w-full max-w-3xl bg-yellow-50 border-2 border-yellow-600 rounded-lg p-6 flex items-start gap-4">
          <div className="flex-shrink-0">
            <svg className="w-8 h-8 text-yellow-600" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          </div>
          <div>
            <h3 className="text-lg font-bold text-yellow-900 mb-2">Proof of Concept</h3>
            <p className="text-yellow-900">
              This is a demonstration system for evaluating RAG capabilities on technical documentation.
              Not for production use with classified data.
            </p>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="features" className="px-6 py-20 bg-white">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl font-bold text-gray-900 mb-4 text-center">How It Works</h2>
          <p className="text-xl text-gray-700 mb-12 text-center max-w-3xl mx-auto">
            Upload up to 10 technical documents (PDF, DOCX) and chat with them using
            AI-powered retrieval and knowledge graph analysis.
          </p>

          <div className="grid md:grid-cols-3 gap-8">
            {/* Feature 1: Hybrid Search */}
            <div className="bg-blue-50 rounded-lg p-6 border border-blue-200">
              <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-2">Hybrid Search</h3>
              <p className="text-gray-700">
                Combines semantic understanding with keyword precision for comprehensive retrieval
                across your document collection.
              </p>
            </div>

            {/* Feature 2: Knowledge Graph */}
            <div className="bg-blue-50 rounded-lg p-6 border border-blue-200">
              <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
                </svg>
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-2">Knowledge Graph</h3>
              <p className="text-gray-700">
                Automatically extracts entities and relationships to understand complex
                connections within technical specifications.
              </p>
            </div>

            {/* Feature 3: Multi-Source Synthesis */}
            <div className="bg-blue-50 rounded-lg p-6 border border-blue-200">
              <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2" />
                </svg>
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-2">Multi-Source Synthesis</h3>
              <p className="text-gray-700">
                Generates comprehensive answers by synthesizing information across
                multiple documents and cross-referencing related content.
              </p>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
