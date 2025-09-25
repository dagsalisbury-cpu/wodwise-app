document.addEventListener('DOMContentLoaded', () => {
    const resultsContainer = document.getElementById('results-container');
    const analyzeButton = document.getElementById('get-percentile-btn');
    const radarChartContainer = document.getElementById('radar-chart-container');
    
    let barCharts = {};
    let radarChart = null;
    const categoryColors = {
        'Olympic Lifting': '#e6194B', 'Strength': '#3cb44b', 'Running': '#4363d8', 'Benchmarks': '#f58231'
    };

    document.querySelectorAll('.input-group').forEach(group => {
        const wodType = group.dataset.wodType;
        const timeInput = group.querySelector('.time-input');
        const scoreInput = group.querySelector('.score-input');
        if (timeInput) timeInput.style.display = (wodType === 'time') ? 'flex' : 'none';
        if (scoreInput) scoreInput.style.display = (wodType !== 'time') ? 'flex' : 'none';
    });

    analyzeButton.addEventListener('click', async () => {
        document.querySelectorAll('.category-row').forEach(row => {
            row.classList.add('hidden');
            row.querySelector('.results-grid').innerHTML = '';
        });

        let summaryData = [];
        const analysisPromises = [];

        for (const wodKey in WOD_CONFIG) {
            const controlSet = document.getElementById(`controls-${wodKey}`);
            if (controlSet) {
                let score = 0;
                if (WOD_CONFIG[wodKey].type === 'time') {
                    const minutes = parseInt(controlSet.querySelector('.minutes-input').value, 10) || 0;
                    const seconds = parseInt(controlSet.querySelector('.seconds-input').value, 10) || 0;
                    score = (minutes * 60) + seconds;
                } else {
                    score = parseInt(controlSet.querySelector('.single-score-input').value, 10) || 0;
                }
                if (score > 0) {
                    analysisPromises.push(processAnalysis(wodKey, score, summaryData));
                }
            }
        }
        await Promise.all(analysisPromises);
        createOrUpdateRadarChart(summaryData);
    });

    async function processAnalysis(wodKey, score, summaryData) {
        const wodConfig = WOD_CONFIG[wodKey];
        const category = wodConfig.category.replace(' ', '-');
        const categoryRow = document.getElementById(`results-${category}`);
        const resultsGrid = categoryRow.querySelector('.results-grid');
        const resultId = `result-${wodKey}`;

        try {
            const response = await fetch(`/api/wod/${wodKey}/percentile`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ score: score }),
            });
            const data = await response.json();
            
            const resultWrapper = document.createElement('div');
            resultWrapper.className = 'result-wrapper';
            resultWrapper.id = resultId;
            resultWrapper.innerHTML = `<div class="percentile-result-container"></div><div class="chart-container"><canvas class="percentile-chart"></canvas></div>`;
            resultsGrid.appendChild(resultWrapper);
            categoryRow.classList.remove('hidden');
            const resultContainer = resultWrapper.querySelector('.percentile-result-container');

            if (data.error) {
                resultContainer.innerHTML = `<p style="color: #ff7f7f;">Error: ${data.error}</p>`;
                return;
            }
            displayResults(resultContainer, data);
            createOrUpdateBarChart(resultId, data);
            summaryData.push({ wodName: data.config.name, percentile: data.percentile });
        } catch (error) {
            console.error('Error:', error);
        }
    }

    function displayResults(container, data) {
        let scoreDisplay;
        if (data.config.type === 'time') {
            const minutes = Math.floor(data.user_score / 60);
            const seconds = (data.user_score % 60).toString().padStart(2, '0');
            scoreDisplay = `${minutes}:${seconds}`;
        } else {
            scoreDisplay = `${data.user_score} ${data.config.unit}`;
        }
        const highlightColor = categoryColors[data.config.category];
        // CHANGE 3 & 4: Simplified title and color-coded score text
        container.innerHTML = `
            <h3>${data.config.name}</h3>
            <p>A score of <strong style="color: ${highlightColor};">${scoreDisplay}</strong> puts you in the <strong style="color: ${highlightColor};">${data.percentile}th percentile</strong>!</p>
        `;
    }

    function createOrUpdateBarChart(resultId, data) {
        const canvas = document.getElementById(resultId).querySelector('.percentile-chart');
        const userScore = data.user_score;
        const highlightColor = categoryColors[data.config.category];
        
        const backgroundColors = data.chart_labels.map((label, index) => {
            const [startStr, endStr] = label.split(' - ');
            let startVal, endVal;
            if (data.config.type === 'time') {
                const [startMin, startSec] = startStr.split(':').map(Number);
                startVal = (startMin * 60) + startSec;
                const [endMin, endSec] = endStr.split(':').map(Number);
                endVal = (endMin * 60) + endSec;
            } else {
                startVal = parseFloat(startStr);
                endVal = parseFloat(endStr);
            }
            let isMatch = (index === data.chart_labels.length - 1) ? (userScore >= startVal && userScore <= endVal) : (userScore >= startVal && userScore < endVal);
            return isMatch ? highlightColor.replace(')', ', 0.8)').replace('rgb', 'rgba') : 'rgba(54, 162, 235, 0.5)';
        });
        if (barCharts[resultId]) barCharts[resultId].destroy();
        barCharts[resultId] = new Chart(canvas, {
            type: 'bar',
            data: { labels: data.chart_labels, datasets: [{ label: 'Number of Athletes', data: data.chart_data, backgroundColor: backgroundColors, borderColor: backgroundColors.map(c => c.replace('0.5', '1').replace('0.8', '1')), borderWidth: 1 }] },
            options: { scales: { y: { beginAtZero: true, ticks: { color: '#e0e0e0' }, grid: { color: '#444' } }, x: { ticks: { color: '#e0e0e0' }, grid: { color: '#444' } } }, plugins: { legend: { display: false }, title: { display: true, text: `Distribution of '${data.config.name}' Scores`, color: '#ffffff', font: { size: 18 } } } }
        });
    }
    
    function createOrUpdateRadarChart(summaryData) {
        if (!radarChartContainer) return;
        radarChartContainer.classList.remove('hidden');
        const canvas = document.getElementById('summaryRadarChart');
        const categoryOrder = ['Olympic Lifting', 'Strength', 'Running', 'Benchmarks'];
        const allWodsSorted = Object.values(WOD_CONFIG).sort((a, b) => {
            const catA = a.category === 'Olympic Lifting' ? 'Strength' : a.category;
            const catB = b.category === 'Olympic Lifting' ? 'Strength' : b.category;
            return categoryOrder.indexOf(catA) - categoryOrder.indexOf(catB);
        });
        const allWodLabels = allWodsSorted.map(wod => wod.name);
        const summaryMap = new Map(summaryData.map(d => [d.wodName, d.percentile]));
        let averagePercentile = 0;
if (summaryData.length > 0) {
    const total = summaryData.reduce((sum, item) => sum + item.percentile, 0);
    averagePercentile = Math.round(total / summaryData.length);
}
const subtitleText = summaryData.length > 0 
    ? `Your average performance is in the ${averagePercentile}th percentile.`
    : 'Enter a score to see your percentile rank.';
        const datasets = categoryOrder.filter(c => c !== 'Olympic Lifting').map(category => {
            const dataForCategory = allWodsSorted.map(wod => {
                const wodCat = wod.category === 'Olympic Lifting' ? 'Strength' : wod.category;
                return (wodCat === category) ? (summaryMap.get(wod.name) || 0) : null
            });
            const pointColors = allWodsSorted.map(wod => {
                const wodCat = wod.category === 'Olympic Lifting' ? 'Strength' : wod.category;
                return (wodCat === category && summaryMap.has(wod.name)) ? '#FFFFFF' : 'rgba(128, 128, 128, 0.7)'
            });
            return {
                label: category,
                data: dataForCategory,
                borderColor: categoryColors[category],
                backgroundColor: categoryColors[category] + '33',
                pointBackgroundColor: pointColors,
                pointBorderColor: "#fff",
                pointRadius: 5,
                pointHoverRadius: 7,
                spanGaps: false
            };
        });
        if (radarChart) radarChart.destroy();
        radarChart = new Chart(canvas, {
            type: 'radar',
            data: { labels: allWodLabels, datasets: datasets },
            options: {
                responsive: true,
        maintainAspectRatio: false,
                layout: {
            padding: {
                top: 10,    // Space at the top of the chart
                bottom: 10,  // Space at the bottom of the chart
            }
        },
                scales: {
                    r: {
                        angleLines: { color: '#555' },
                        grid: { color: '#555' },
                        pointLabels: { color: '#e0e0e0', font: { size: 12 } },
                        ticks: { color: '#e0e0e0', backdropColor: '#1e1e1e', stepSize: 25 },
                        min: 0,
                        max: 100
                    }
                },
                plugins: {
    legend: {
    display: true,
    position: 'right',
    labels: {
        color: '#e0e0e0',
        font: { size: 14 }
    },
    // This adds an invisible title that acts as a spacer
    title: {
        display: true,
        text: ' ', // The title's text is just an empty space
        padding: {
            left: 30,// This creates the 30px gap you want
        }
    }
},
    title: { display: true, text: 'Overall Performance Profile', color: '#ffffff', font: { size: 20 } },
    // --- Add this new subtitle section ---
    subtitle: {
        display: true,
        text: subtitleText, // This uses the variable we created
        color: '#b3b3b3',
        font: { size: 14, style: 'italic' },
        padding: {
            bottom: 0 // Adds some space between the subtitle and the legend
        }
    }
}
            }
        });
    }

    createOrUpdateRadarChart([]);
});