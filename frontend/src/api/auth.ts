import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch, getAuthToken, setAuthToken } from './client';
import type { Role, User } from '../types';

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: {
    id: string;
    email: string;
    role: Role;
    is_active: boolean;
  };
}

export async function loginUser(email: string, password: string): Promise<LoginResponse> {
  const res = await apiFetch<LoginResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  setAuthToken(res.access_token);
  return res;
}

export async function fetchCurrentUser(): Promise<User | null> {
  const token = getAuthToken();
  if (!token) return null;

  try {
    const data = await apiFetch<{
      id: string;
      email: string;
      role: Role;
      is_active: boolean;
    }>('/auth/me');

    return {
      id: data.id,
      email: data.email,
      fullName: data.email,
      role: data.role,
    };
  } catch {
    setAuthToken(null);
    return null;
  }
}

export function useCurrentUser() {
  return useQuery({
    queryKey: ['currentUser'],
    queryFn: fetchCurrentUser,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      loginUser(email, password),
    onSuccess: (data) => {
      queryClient.setQueryData(['currentUser'], {
        id: data.user.id,
        email: data.user.email,
        fullName: data.user.email,
        role: data.user.role,
      });
      queryClient.invalidateQueries();
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return () => {
    setAuthToken(null);
    queryClient.clear();
  };
}
