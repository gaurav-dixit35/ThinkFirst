'use client';
import {useEffect, useState} from 'react';

export function useAttemptDraft(id: string) {
  const [attempt, setAttempt] = useState('');
  const [partial, setPartial] = useState(true);
  const [loaded, setLoaded] = useState(false);
  const [storageError, setStorageError] = useState('');
  useEffect(() => {
    try {
      const value = localStorage.getItem(`thinkfirst.draft.${id}`);
      if (value) {
        const draft = JSON.parse(value);
        setAttempt(typeof draft.attempt === 'string' ? draft.attempt : '');
        setPartial(draft.partial !== false);
      }
    } catch {setStorageError('Draft recovery is unavailable in this browser. Save your attempt before leaving.');}
    setLoaded(true);
  }, [id]);
  useEffect(() => {
    if (!loaded) return;
    try {
      if (attempt) localStorage.setItem(`thinkfirst.draft.${id}`, JSON.stringify({attempt, partial}));
      else localStorage.removeItem(`thinkfirst.draft.${id}`);
    } catch {setStorageError('Your draft could not be stored on this device. Keep this page open until your attempt is saved.');}
  }, [attempt, partial, loaded, id]);
  return {attempt, setAttempt, partial, setPartial, storageError};
}
