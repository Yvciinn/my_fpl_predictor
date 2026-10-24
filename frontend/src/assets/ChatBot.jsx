import React, { useState, useRef, useEffect } from 'react'
import { sendChat } from '../services/api'

const MAX_LEN = 500 // must match the limit in api.py

const SUGGESTIONS = [
    'Who is the best captain this week?',
    'Is my squad any good?',
    'Which defenders are best value?'
]

export default function ChatBot({ squadIds = [] }) {
    const [open, setOpen] = useState(false)
    const [input, setInput] = useState('')
    const [loading, setLoading] = useState(false)
    const [messages, setMessages] = useState([
        {
            role: 'bot',
            text: 'Ask me about players, fixtures or your squad.'
        }
    ])

    const endRef = useRef(null)

    // keep the latest message in view
    useEffect(() => {
        endRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages, loading, open])

    const send = async (text) => {
        const message = text.trim()
        if (!message || loading) return

        setMessages(prev => [...prev, { role: 'user', text: message }])
        setInput('')
        setLoading(true)

        try {
            // squad is optional on the backend: send null when nothing is picked
            const res = await sendChat(message, squadIds.length ? squadIds : null)
            setMessages(prev => [...prev, { role: 'bot', text: res.data.answer }])
        } catch (err) {
            const detail =
                err.response?.data?.detail || 'Could not reach the assistant. Try again.'
            setMessages(prev => [...prev, { role: 'bot', text: detail, error: true }])
        } finally {
            setLoading(false)
        }
    }

    const onKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            send(input)
        }
    }

    if (!open) {
        return (
            <button
                className='chat-fab'
                onClick={() => setOpen(true)}
                aria-label='Open assistant'
            >
                Ask the assistant
            </button>
        )
    }

    return (
        <div className='chat-panel' role='dialog' aria-label='Assistant'>
            <div className='chat-header'>
                <div>
                    <strong>Assistant</strong>
                    <span className='chat-sub'>
                        {squadIds.length
                            ? `Using your ${squadIds.length} picked players`
                            : 'No squad selected'}
                    </span>
                </div>
                <button
                    className='chat-close'
                    onClick={() => setOpen(false)}
                    aria-label='Close assistant'
                >
                    ×
                </button>
            </div>

            <div className='chat-messages' aria-live='polite'>
                {messages.map((m, i) => (
                    <div
                        key={i}
                        className={`chat-msg ${m.role}${m.error ? ' error' : ''}`}
                    >
                        {m.text}
                    </div>
                ))}

                {loading && (
                    <div className='chat-msg bot typing' aria-label='Assistant is typing'>
                        <span /><span /><span />
                    </div>
                )}

                {messages.length === 1 && !loading && (
                    <div className='chat-suggestions'>
                        {SUGGESTIONS.map(s => (
                            <button key={s} onClick={() => send(s)}>{s}</button>
                        ))}
                    </div>
                )}

                <div ref={endRef} />
            </div>

            <div className='chat-input-row'>
                <textarea
                    rows={1}
                    value={input}
                    maxLength={MAX_LEN}
                    placeholder='Type your question...'
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={onKeyDown}
                    disabled={loading}
                />
                <button
                    onClick={() => send(input)}
                    disabled={loading || !input.trim()}
                >
                    Send
                </button>
            </div>
        </div>
    )
}