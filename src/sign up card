import React, { useState } from 'react';
import TextInput from './TextInput';
import Button from './Button';

// 1. Accept 'onSwitch' prop here
const SignUpCard = ({ onSwitch }) => {
  const [formData, setFormData] = useState({
    fullName: '', email: '', password: '', confirmPassword: '',
  });

  const handleChange = (field, value) => {
    setFormData({ ...formData, [field]: value });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (formData.password !== formData.confirmPassword) {
      alert("Passwords do not match!");
      return;
    }
    alert("Account Created!");
  };

  return (
    <div style={styles.card}>
      <div style={styles.header}>
        <h2 style={styles.title}>Get Started</h2>
        <p style={styles.subtitle}>Create an account to explore new business ventures.</p>
      </div>

      <form onSubmit={handleSubmit}>
        <TextInput label="Full Name" placeholder="John Doe" value={formData.fullName} onChange={(val) => handleChange('fullName', val)} />
        <TextInput label="Email Address" type="email" placeholder="name@company.com" value={formData.email} onChange={(val) => handleChange('email', val)} />
        <TextInput label="Password" type="password" placeholder="Create a password" value={formData.password} onChange={(val) => handleChange('password', val)} />
        <TextInput label="Confirm Password" type="password" placeholder="Confirm your password" value={formData.confirmPassword} onChange={(val) => handleChange('confirmPassword', val)} />

        <div style={styles.checkboxContainer}>
          <input type="checkbox" id="terms" required style={{ marginRight: '8px' }} />
          <label htmlFor="terms" style={{ fontSize: '12px', color: '#6B7280' }}>
             I agree to the <a href="#" style={styles.link}>Terms</a>
          </label>
        </div>

        <Button label="Create Account" onClick={handleSubmit} type="submit" />
      </form>

      <div style={styles.footer}>
        <span style={{ color: 'gray' }}>Already have an account? </span>
        {/* 2. Use 'onSwitch' here instead of href */}
        <button onClick={onSwitch} style={styles.textButton}>
          Log in
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
  checkboxContainer: { display: 'flex', alignItems: 'center', marginBottom: '20px' },
  link: { color: '#2563EB', textDecoration: 'none' },
  footer: { textAlign: 'center', marginTop: '20px', fontSize: '14px' },
  // New style to make the button look like a link
  textButton: { background: 'none', border: 'none', color: '#2563EB', fontWeight: 'bold', cursor: 'pointer', fontSize: '14px', padding: 0, textDecoration: 'underline' }
};

export default SignUpCard;