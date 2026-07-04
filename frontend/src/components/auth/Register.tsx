// AutoPrism - Register Component
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/stores';
import { Button, Input, GlassCard } from '@/components/ui';

export default function Register() {
  const navigate = useNavigate();
  const { register, isLoading } = useAuthStore();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    try {
      await register(email, password);
      navigate('/');
    } catch (err) {
      setError('Registration failed. Email may already be in use.');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <GlassCard opacity={0.15} className="w-full max-w-md p-8">
        <h1 className="text-2xl font-bold text-gradient mb-2">创建账号</h1>
        <p className="text-white/60 mb-6">开始构建你的技术情报系统</p>

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
            placeholder="至少6位"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <Input
            type="password"
            label="确认密码"
            placeholder="••••••••"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
          />
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <Button type="submit" variant="primary" disabled={isLoading}>
            {isLoading ? '注册中...' : '注册'}
          </Button>
        </form>

        <p className="mt-4 text-center text-sm text-white/50">
          已有账号？{' '}
          <a href="/login" className="text-nebula-purple hover:underline">
            登录
          </a>
        </p>
      </GlassCard>
    </div>
  );
}