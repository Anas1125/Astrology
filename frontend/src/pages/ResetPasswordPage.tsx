import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { ArrowRight, LockKeyhole, Eye, EyeOff } from 'lucide-react';
import { Link } from 'react-router-dom';
import { ApiError, resetPassword } from '../auth/api';
import { useAstroLanguage } from '../auth/language';
import { AuthLayout } from './LoginPage';

export const resetPasswordText = {
  en: {
    eyebrow: 'ACCOUNT RECOVERY', title: 'Choose a new password', subtitle: 'Use a unique password between 12 and 128 characters.', password: 'New password', confirm: 'Confirm new password', hint: 'Use at least 12 characters.', short: 'Enter at least 12 characters.', validLength: 'Password length meets the minimum.', submit: 'Update password', submitting: 'Updating…', back: 'Back to log in', success: 'Your password has been updated. Sign in with the new password.', mismatch: 'The passwords do not match.', invalid: 'This reset link is invalid, expired, or already used. Request a new link.', failed: 'We could not update your password. Please try again.', show: 'Show password', hide: 'Hide password',
  },
  ta: {
    eyebrow: 'கணக்கு மீட்பு', title: 'புதிய கடவுச்சொல்லைத் தேர்ந்தெடுக்கவும்', subtitle: '12 முதல் 128 எழுத்துகள் கொண்ட தனித்துவமான கடவுச்சொல்லைப் பயன்படுத்தவும்.', password: 'புதிய கடவுச்சொல்', confirm: 'புதிய கடவுச்சொல்லை உறுதிப்படுத்தவும்', hint: 'குறைந்தது 12 எழுத்துகள் இருக்க வேண்டும்.', short: 'குறைந்தது 12 எழுத்துகளை உள்ளிடவும்.', validLength: 'கடவுச்சொல் குறைந்தபட்ச நீளத்தை அடைகிறது.', submit: 'கடவுச்சொல்லைப் புதுப்பி', submitting: 'புதுப்பிக்கப்படுகிறது…', back: 'உள்நுழைவுக்குத் திரும்பு', success: 'கடவுச்சொல் புதுப்பிக்கப்பட்டது. புதிய கடவுச்சொல்லுடன் உள்நுழையவும்.', mismatch: 'கடவுச்சொற்கள் பொருந்தவில்லை.', invalid: 'இந்த மீட்டமைப்பு இணைப்பு தவறானது, காலாவதியானது அல்லது ஏற்கனவே பயன்படுத்தப்பட்டது. புதிய இணைப்பைக் கோரவும்.', failed: 'கடவுச்சொல்லைப் புதுப்பிக்க முடியவில்லை. மீண்டும் முயற்சிக்கவும்.', show: 'கடவுச்சொல்லைக் காட்டு', hide: 'கடவுச்சொல்லை மறை',
  },
} as const;

export default function ResetPasswordPage() {
  const [language] = useAstroLanguage();
  const t = resetPasswordText[language];
  const [token] = useState(() => typeof window === 'undefined' ? '' : new URLSearchParams(window.location.hash.replace(/^#/, '')).get('token') ?? '');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (token && window.location.hash) window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}`);
  }, [token]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError('');
    if (password !== confirmation) { setError(t.mismatch); return; }
    setSubmitting(true);
    try { await resetPassword(token, password); setSuccess(true); }
    catch (reason) { setError(reason instanceof ApiError && reason.status === 400 ? t.invalid : t.failed); }
    finally { setSubmitting(false); }
  }

  return <AuthLayout eyebrow={t.eyebrow} title={t.title} subtitle={t.subtitle}>
    {success ? <div className="auth-success" role="status">{t.success}</div> : !token ? <p className="auth-error" role="alert">{t.invalid}</p> : <form className="auth-form" onSubmit={submit}>
      <label htmlFor="reset-password">{t.password}</label><div className="auth-input"><LockKeyhole size={17}/><input id="reset-password" type={showPassword ? 'text' : 'password'} autoComplete="new-password" minLength={12} maxLength={128} required value={password} onChange={event => setPassword(event.target.value)}/><button className="password-toggle" type="button" aria-label={showPassword ? t.hide : t.show} onClick={() => setShowPassword(value => !value)}>{showPassword ? <EyeOff size={16}/> : <Eye size={16}/>}</button></div>
      <small className="password-strength-hint" role="status">{password.length < 12 ? t.short : t.validLength}</small>
      <label htmlFor="reset-confirm-password">{t.confirm}</label><div className="auth-input"><LockKeyhole size={17}/><input id="reset-confirm-password" type={showConfirmation ? 'text' : 'password'} autoComplete="new-password" minLength={12} maxLength={128} required value={confirmation} onChange={event => setConfirmation(event.target.value)}/><button className="password-toggle" type="button" aria-label={showConfirmation ? t.hide : t.show} onClick={() => setShowConfirmation(value => !value)}>{showConfirmation ? <EyeOff size={16}/> : <Eye size={16}/>}</button></div>
      {confirmation && password !== confirmation && <small className="password-strength-hint" role="status">{t.mismatch}</small>}
      {error && <p className="auth-error" role="alert">{error}</p>}
      <button className="auth-submit" type="submit" disabled={submitting}>{submitting ? t.submitting : t.submit} <ArrowRight size={16}/></button>
    </form>}
    <p className="auth-switch"><Link to="/login">{t.back}</Link></p>
  </AuthLayout>;
}
