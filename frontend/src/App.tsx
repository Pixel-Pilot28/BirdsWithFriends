import { Routes, Route } from 'react-router-dom';
import Navbar from '@/components/Navbar';
import LivePage from '@/pages/LivePage';
import StoriesPage from '@/pages/StoriesPage';
import CharactersPage from '@/pages/CharactersPage';
import NotificationsPage from '@/pages/NotificationsPage';

function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <main className="container mx-auto px-4 py-8">
        <Routes>
          <Route path="/" element={<LivePage />} />
          <Route path="/stories" element={<StoriesPage />} />
          <Route path="/characters" element={<CharactersPage />} />
          <Route path="/notifications" element={<NotificationsPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;