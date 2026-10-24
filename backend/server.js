const express = require("express")
const cors = require("cors")
const dotenv = require("dotenv")
dotenv.config()


const connectDb = require("./config/config")

const app = express()

app.use(cors())
app.use(express.json())

connectDb()

const PORT = process.env.PORT || 3000

app.get("/", (req, res) => {
    res.json({ message: "hello" })
})

app.listen(PORT, () => {
    console.log(`App is listening on port ${PORT}`)
})
app.use('/api/players', require('./routes/players'))
app.use('/api/chat', require('./routes/chat'))