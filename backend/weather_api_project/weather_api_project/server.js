require('dotenv').config();
const axios = require('axios');
const express = require("express");

const app = express();
const PORT = 3000;

// -------------------------------------------
// WEATHER ROUTE (Direct from OpenWeather API)
// -------------------------------------------
app.get("/weather/:city", async (req, res) => {
  const city = req.params.city;   // get city from URL

  if (!city) {
    return res.status(400).json({ error: "City is required" });
  }

  try {
    const apiKey = process.env.WEATHER_KEY;

    const url = `https://api.openweathermap.org/data/2.5/weather?q=${city}&appid=${apiKey}&units=metric`;

    const response = await axios.get(url);
    const data = response.data;

    res.json({
      success: true,
      city: data.name,
      temperature: data.main.temp,
      humidity: data.main.humidity,
      feels_like: data.main.feels_like,
      description: data.weather[0].description,
    });

  } catch (error) {
    console.log(error.response?.data || error.message);
    res.status(500).json({ error: "Unable to fetch weather data" });
  }
});

// -------------------------------------------
// START SERVER
// -------------------------------------------
app.listen(PORT, () =>
  console.log(`Server running at http://localhost:${PORT}`)
);
