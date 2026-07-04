// AutoPrism - Auth Components
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/stores';
import { Button, Input, GlassCard } from '@/components/ui';

export default function Login() {
  const navigate = useNavigate();
  const { login, isLoading } = useAuthStore();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await login(email, password);
      navigate('/');
    } catch (err) {
      setError('Invalid email or password');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <GlassCard opacity={0.15} className="w-full max-w-md p-8">
        <h1 className="text-2xl font-bold text-gradient mb-2">AutoPrism</h1>
        <p className="text-white/60 mb-6">登录以继续</p>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <Input
            type="email"
            label="邮箱"
            placeholder="your@email.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <Input
            type="password"
            label="密码"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <Button type="submit" variant="primary" disabled={isLoading}>
            {isLoading ? '登录中...' : '登录'}
          </Button>
        </form>

        <p className="mt-4 text-center text-sm text-white/50">
          还没有账号？{' '}
          <a href="/register" className="text-nebula-purple hover:underline">
            注册
          </a>
        </p>
      </GlassCard>
    </div>
  );
}