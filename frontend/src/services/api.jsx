import axios from 'axios'

const API = axios.create({
    baseURL: 'http://localhost:5000/api'
})

export const getTopPlayers = (gw) => API.get(`/players/${gw}/top`)
export const getAllPlayers = (gw) => API.get(`/players/${gw}/all`, {
    headers: { 'Cache-Control': 'no-cache' }
})
export const getBestTeam   = (gw) => API.get(`/players/${gw}`)

// chatbot: goes Node (/api/chat) -> FastAPI (/chat)
export const sendChat = (message, squad) => API.post('/chat', { message, squad })