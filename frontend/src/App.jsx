import React from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import Header from './assets/header'
import Home from './pages/Home'
import SquadBuilder from './pages/SquadBuilder'

function App() {
  return (
    <BrowserRouter>
      <Header />
      <Routes>
        <Route path="/" element={<Home></Home>}></Route>
        <Route path="/squad" element={<SquadBuilder />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App