import React from 'react'
import { Link } from 'react-router-dom'

export default function Header() {
    return (
        <div className='header'>
            <div className='photo'>
                <img src="logo.png" alt="logo" />
            </div>
            <div className='nav'>
                <Link to="/">Home</Link>
                <Link to="/squad">Build team</Link>
                <a href="#">About</a>
                <a href="#">Contact</a>
            </div>
        </div>
    )
}