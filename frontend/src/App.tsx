import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
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
      <ToastContainer
        position="bottom-right"
        autoClose={5000}
        hideProgressBar={false}
        newestOnTop={false}
        closeOnClick
        rtl={false}
        pauseOnFocusLoss
        draggable
        pauseOnHover
        theme="light"
      />
    </div>
  );
}

export default App;