async function get(endpoint) {
	const response = await fetch(endpoint);
	if (!response.ok) {
		throw new Error(`HTTP error! status: ${response.status}`);
	}
	return response.json();
}

async function getStations(query) {
	const stations = await get(`/stations/search/${query}`);
	const stationId = stations[0].station_id;
	const departures = await get(`/stations/${stationId}/departures`);
	const arrivals = await get(`/stations/${stationId}/arrivals`);
	updateDepartures("departures", departures);
	updateArrivals("arrivals", arrivals);
}

async function getTrainStatus(trainNumber, originId, departureDate) {
	const train = await get(
		`/trains/?train_number=${trainNumber}&origin_station_id=${originId}&departure_date=${departureDate}`,
	);
	updateTrainStatus(train);
}

document.querySelector("#search-button").addEventListener("click", async () => {
	const query = document.getElementById("search").value;
	await getStations(query);
});

function updateDepartures(tableId, data) {
	const tbody = document.getElementById(tableId);
	tbody.innerHTML = "";
	for (const item of data) {
		const row = document.createElement("tr");
		row.dataset.trainNumber = item.number;
		row.dataset.originStationId = item.origin_station_id;
		row.dataset.departureDate = item.departure_date;
		row.innerHTML = `
      <td>${item.number}</td>
      <td>${item.destination}</td>
       <td>${new Date(item.departure_time).toLocaleTimeString([], {
					hour: "2-digit",
					minute: "2-digit",
				})}</td>
      <td>${item.delay}</td>
      <td>${item.scheduled_track || item.actual_track}</td>
    `;
		tbody.appendChild(row);
	}
}

function updateArrivals(tableId, data) {
	const tbody = document.getElementById(tableId);
	tbody.innerHTML = "";
	for (const item of data) {
		const row = document.createElement("tr");
		row.dataset.trainNumber = item.number;
		row.dataset.originStationId = item.origin_station_id;
		row.dataset.departureDate = item.departure_date;
		row.innerHTML = `
       <td class="train-number">${item.number}</td>
       <td class="station">${item.origin}</td>
       <td>${new Date(item.arrival_time).toLocaleTimeString([], {
					hour: "2-digit",
					minute: "2-digit",
				})}</td>
       <td>${item.delay}</td>
       <td>${item.scheduled_track || item.actual_track}</td>
     `;
		tbody.appendChild(row);
	}
}

function updateTrainStatus(train) {
	document.getElementById("train-number").textContent = train.number;
	document.querySelector(".departure-time").textContent = new Date(
		train.departure_time,
	).toLocaleTimeString([], {
		hour: "2-digit",
		minute: "2-digit",
	});
	document.querySelector(".departure-station").textContent = train.origin;
	document.querySelector(".arrival-time").textContent = new Date(
		train.arrival_time,
	).toLocaleTimeString([], {
		hour: "2-digit",
		minute: "2-digit",
	});
	document.querySelector(".arrival-station").textContent = train.destination;

	const stops = document.getElementById("stops");
	stops.innerHTML = "";
	for (const stop of train.stops) {
		const li = document.createElement("li");
		li.innerHTML = `
      <a class="stop-name">${stop.name}</a> · <span class="track">${
				stop.actual_departure_track || stop.scheduled_departure_track
			}</span>
      <br />
      Partenza:
      <time class="scheduled-departure-time">${new Date(
				stop.scheduled_departure_time,
			).toLocaleTimeString([], {
				hour: "2-digit",
				minute: "2-digit",
			})}</time>
      <time class="actual-departure-time">${new Date(
				stop.actual_departure_time,
			).toLocaleTimeString([], {
				hour: "2-digit",
				minute: "2-digit",
			})}</time>

      ${
				stop.actual_arrival_time
					? `
      <br />
      Arrivo:
      <time class="scheduled-arrival-time">${new Date(
				stop.scheduled_arrival_time,
			).toLocaleTimeString([], {
				hour: "2-digit",
				minute: "2-digit",
			})}</time>
      <time class="actual-arrival-time">${new Date(
				stop.actual_arrival_time,
			).toLocaleTimeString([], {
				hour: "2-digit",
				minute: "2-digit",
			})}</time>
      `
					: ""
			}
    `;
		stops.appendChild(li);
	}
}

document
	.querySelector("#departures")
	.addEventListener("click", async (event) => {
		if (event.target.tagName === "TD") {
			const trainNumber = event.target.parentElement.dataset.trainNumber;
			const originId = event.target.parentElement.dataset.originStationId;
			const departureDate = event.target.parentElement.dataset.departureDate;
			await getTrainStatus(trainNumber, originId, departureDate);
		}
	});

document.querySelector("#arrivals").addEventListener("click", async (event) => {
	if (event.target.tagName === "TD") {
		const trainNumber = event.target.parentElement.dataset.trainNumber;
		const originId = event.target.parentElement.dataset.originStationId;
		const departureDate = event.target.parentElement.dataset.departureDate;
		await getTrainStatus(trainNumber, originId, departureDate);
	}
});

document.querySelector("#stops").addEventListener("click", async (event) => {
	if (event.target.tagName === "A") {
		const stationName = event.target.textContent;
		await getStations(stationName);
	}
});

document.querySelector("#search").addEventListener("keydown", async (event) => {
	if (event.key === "Enter") {
		const query = document.getElementById("search").value;
		await getStations(query);
	}
});
