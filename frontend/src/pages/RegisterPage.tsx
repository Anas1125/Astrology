import { useState } from 'react';
import type { FormEvent } from 'react';
import { ArrowRight, Eye, EyeOff, LockKeyhole, Mail } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { AuthLayout } from './LoginPage';
import { useAuth } from '../auth/AuthContext';

export default function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError('');
    if (password.length < 12) { setError('Use at least 12 characters for your password.'); return; }
    if (password !== confirmPassword) { setError('Your passwords do not match.'); return; }
    setSubmitting(true);
    try { await register(email.trim(), password); navigate('/app', { replace: true }); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to create your account. Please try again.'); }
    finally { setSubmitting(false); }
  }

  return <AuthLayout eyebrow="YOUR JOURNEY STARTS HERE" title="Create your account." subtitle="A private space for your birth profiles and astrology readings."><form className="auth-form" onSubmit={handleSubmit}>
    <label htmlFor="register-email">Email address</label><div className="auth-input"><Mail size={17}/><input id="register-email" type="email" autoComplete="email" required maxLength={320} value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com"/></div>
    <label htmlFor="register-password">Password <span className="field-hint">12 characters minimum</span></label><div className="auth-input"><LockKeyhole size={17}/><input id="register-password" type={showPassword ? 'text' : 'password'} autoComplete="new-password" required minLength={12} maxLength={128} value={password} onChange={e => setPassword(e.target.value)} placeholder="Create a strong password"/><button type="button" className="password-toggle" aria-label={showPassword ? 'Hide password' : 'Show password'} onClick={() => setShowPassword(!showPassword)}>{showPassword ? <EyeOff size={16}/> : <Eye size={16}/>}</button></div>
    <label htmlFor="confirm-password">Confirm password</label><div className="auth-input"><LockKeyhole size={17}/><input id="confirm-password" type={showPassword ? 'text' : 'password'} autoComplete="new-password" required value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} placeholder="Enter your password again"/></div>
    <p className="auth-note">Your name can be added to your personal birth profile after signup. The current account API registers with email and password.</p>
    {error && <p className="auth-error" role="alert">{error}</p>}<button className="auth-submit" type="submit" disabled={submitting}>{submitting ? 'Creating account…' : 'Create account'} <ArrowRight size={16}/></button>
  </form><p className="auth-switch">Already have an account? <Link to="/login">Log in</Link></p></AuthLayout>;
}
