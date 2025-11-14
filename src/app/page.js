
'use client';
import { useState } from 'react';
import { signUp, signIn, logOut } from '@/firebase/auth';
import { createDoc } from '@/firebase/database';

export default function Home() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');

  const handleSignUp = async () => {
    try {
      const userCredential = await signUp(email, password);
      setMessage('✅ User created: ' + userCredential.user.email);
      
      // Créer un doc dans Firestore
      await createDoc('users', {
        email: userCredential.user.email,
        createdAt: new Date()
      });
    } catch (error) {
      setMessage('❌ ' + error.message);
    }
  };

  const handleSignIn = async () => {
    try {
      const userCredential = await signIn(email, password);
      setMessage('✅ Logged in: ' + userCredential.user.email);
    } catch (error) {
      setMessage('❌ ' + error.message);
    }
  };

  const handleLogOut = async () => {
    try {
      await logOut();
      setMessage('✅ Logged out');
    } catch (error) {
      setMessage('❌ ' + error.message);
    }
  };

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-6">🚀 Apollo - Firebase Test</h1>
      
      <div className="mb-4">
        <input 
          type="email" 
          placeholder="Email" 
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="border p-2 mr-2 rounded"
        />
        <input 
          type="password" 
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="border p-2 mr-2 rounded"
        />
      </div>

      <div className="space-x-2 mb-4">
        <button 
          onClick={handleSignUp}
          className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
        >
          Sign Up
        </button>
        <button 
          onClick={handleSignIn}
          className="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600"
        >
          Sign In
        </button>
        <button 
          onClick={handleLogOut}
          className="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600"
        >
          Log Out
        </button>
      </div>

      {message && (
        <div className="mt-4 p-4 bg-gray-100 rounded">
          {message}
        </div>
      )}
    </div>
  );
}
