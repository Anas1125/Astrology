import { useState } from 'react';
import type { FormEvent } from 'react';
import { ArrowRight, Mail } from 'lucide-react';
import { Link } from 'react-router-dom';
import { requestPasswordReset } from '../auth/api';
import { useAstroLanguage } from '../auth/language';
import { AuthLayout } from './LoginPage';

export const forgotPasswordText = {
  en: {
    eyebrow: 'ACCOUNT RECOVERY', title: 'Reset your password', subtitle: 'Enter your account email. If it is registered and delivery is available, we will send reset instructions.', email: 'Email address', submit: 'Send reset instructions', sending: 'Sending…', back: 'Back to log in', sent: 'If the address is registered and email delivery is available, reset instructions will be sent. Check your inbox and spam folder.', unavailable: 'Password reset email is not configured on this server. Please contact the administrator.', failed: 'We could not process this request. Please try again later.',
  },
  ta: {
    eyebrow: 'கணக்கு மீட்பு', title: 'கடவுச்சொல்லை மீட்டமைக்கவும்', subtitle: 'உங்கள் கணக்கு மின்னஞ்சலை உள்ளிடவும். அது பதிவு செய்யப்பட்டு மின்னஞ்சல் சேவை இருந்தால், மீட்டமைப்பு வழிமுறைகள் அனுப்பப்படும்.', email: 'மின்னஞ்சல் முகவரி', submit: 'மீட்டமைப்பு வழிமுறைகளை அனுப்பு', sending: 'அனுப்பப்படுகிறது…', back: 'உள்நுழைவுக்குத் திரும்பு', sent: 'இந்த முகவரி பதிவு செய்யப்பட்டு மின்னஞ்சல் சேவை இருந்தால், மீட்டமைப்பு வழிமுறைகள் அனுப்பப்படும். இன்பாக்ஸ் மற்றும் ஸ்பேம் கோப்புறையைப் பார்க்கவும்.', unavailable: 'இந்த சேவையகத்தில் கடவுச்சொல் மீட்டமைப்பு மின்னஞ்சல் அமைக்கப்படவில்லை. நிர்வாகியைத் தொடர்புகொள்ளவும்.', failed: 'இந்த கோரிக்கையைச் செயல்படுத்த முடியவில்லை. பின்னர் மீண்டும் முயற்சிக்கவும்.',
  },
} as const;

export default function ForgotPasswordPage() {
  const [language] = useAstroLanguage();
  const t = forgotPasswordText[language];
  const [email, setEmail] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(''); setSubmitting(true);
    try { await requestPasswordReset(email.trim()); setSent(true); }
    catch (reason) {
      const status = typeof reason === 'object' && reason !== null && 'status' in reason ? Number(reason.status) : 0;
      setError(status === 503 ? t.unavailable : t.failed);
    } finally { setSubmitting(false); }
  }

  return <AuthLayout eyebrow={t.eyebrow} title={t.title} subtitle={t.subtitle}>
    {sent ? <div className="auth-success" role="status">{t.sent}</div> : <form className="auth-form" onSubmit={submit}>
      <label htmlFor="forgot-email">{t.email}</label><div className="auth-input"><Mail size={17}/><input id="forgot-email" type="email" autoComplete="email" required maxLength={320} value={email} onChange={event => setEmail(event.target.value)} placeholder="you@example.com"/></div>
      {error && <p className="auth-error" role="alert">{error}</p>}
      <button className="auth-submit" type="submit" disabled={submitting}>{submitting ? t.sending : t.submit} <ArrowRight size={16}/></button>
    </form>}
    <p className="auth-switch"><Link to="/login">{t.back}</Link></p>
  </AuthLayout>;
}
