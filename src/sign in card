import React, { useState } from 'react';
import TextInput from './TextInput';
import Button from './Button';

// 1. Accept 'onSwitch' prop here
const SignInCard = ({ onSwitch }) => {
  const [formData, setFormData] = useState({ email: '', password: '' });

  const handleChange = (field, value) => {
    setFormData({ ...formData, [field]: value });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    alert(`Signing in as: ${formData.email}`);
  };

  return (
    <div style={styles.card}>
      <div style={styles.header}>
        <h2 style={styles.title}>Welcome Back</h2>
        <p style={styles.subtitle}>Enter your credentials to access business opportunities.</p>
      </div>

      <form onSubmit={handleSubmit}>
        <TextInput label="Email Address" type="email" placeholder="name@company.com" value={formData.email} onChange={(val) => handleChange('email', val)} />
        <TextInput label="Password" type="password" placeholder="Enter your password" value={formData.password} onChange={(val) => handleChange('password', val)} />
        
        <div style={{ textAlign: 'right', marginBottom: '10px' }}>
          <a href="#" style={styles.link}>Forgot password?</a>
        </div>

        <Button label="Sign In" type="submit" />
      </form>

      <div style={styles.footer}>
        <span style={{ color: 'gray' }}>Don't have an account? </span>
        {/* 2. Use 'onSwitch' here */}
        <button onClick={onSwitch} style={styles.textButton}>
          Create an account
        </button>
      </div>
    </div>
  );
};

const styles = {
  card: { backgroundColor: 'white', padding: '40px', borderRadius: '16px', boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)', maxWidth: '400px', width: '100%', margin: '20px auto', fontFamily: 'Arial, sans-serif' },
  header: { textAlign: 'center', marginBottom: '20px' },
  title: { margin: '0 0 10px 0', fontSize: '24px', color: '#111827' },
  subtitle: { margin: 0, color: '#6B7280', fontSize: '14px' },
  link: { color: '#2563EB', textDecoration: 'none', fontSize: '12px' },
  footer: { textAlign: 'center', marginTop: '20px', fontSize: '14px' },
  textButton: { background: 'none', border: 'none', color: '#2563EB', fontWeight: 'bold', cursor: 'pointer', fontSize: '14px', padding: 0, textDecoration: 'underline' }
};

export default SignInCard;