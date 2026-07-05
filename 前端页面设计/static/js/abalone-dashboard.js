window.AbaloneCharts = (function () {
    function parseJsonAttr(el, name, fallback) {
        if (!el) return fallback;
        var raw = el.getAttribute(name);
        if (!raw) return fallback;
        try { return JSON.parse(raw); } catch (err) { return fallback; }
    }

    function themeChart(chart) {
        window.addEventListener('resize', function () { chart.resize(); });
        return chart;
    }

    function bar(id, title, seriesName, color) {
        var el = document.getElementById(id);
        if (!el || !window.echarts) return;
        var x = parseJsonAttr(el, 'data-x', []);
        var y = parseJsonAttr(el, 'data-y', []);
        var chart = themeChart(echarts.init(el));
        chart.setOption({
            title: { text: title, textStyle: { color: '#16313b', fontWeight: 800 } },
            tooltip: { trigger: 'axis' },
            grid: { left: 42, right: 20, top: 58, bottom: 36 },
            xAxis: { type: 'category', data: x, axisLine: { lineStyle: { color: '#9eb8b6' } } },
            yAxis: { type: 'value', splitLine: { lineStyle: { color: '#e4efed' } } },
            series: [{
                name: seriesName,
                type: 'bar',
                data: y,
                barWidth: 18,
                itemStyle: { color: color || '#0e8f9f', borderRadius: [6, 6, 0, 0] }
            }]
        });
    }

    function pie(id) {
        var el = document.getElementById(id);
        if (!el || !window.echarts) return;
        var data = parseJsonAttr(el, 'data-series', []);
        var chart = themeChart(echarts.init(el));
        chart.setOption({
            tooltip: { trigger: 'item' },
            legend: { bottom: 0, textStyle: { color: '#dff9f7' } },
            series: [{
                type: 'pie',
                radius: ['42%', '70%'],
                data: data,
                itemStyle: { borderColor: '#06232f', borderWidth: 2 },
                label: { color: '#dff9f7' }
            }]
        });
    }

    function line(id, seriesName) {
        var el = document.getElementById(id);
        if (!el || !window.echarts) return;
        var x = parseJsonAttr(el, 'data-x', []);
        var y = parseJsonAttr(el, 'data-y', []);
        var chart = themeChart(echarts.init(el));
        chart.setOption({
            tooltip: { trigger: 'axis' },
            grid: { left: 42, right: 20, top: 30, bottom: 36 },
            xAxis: { type: 'category', data: x, axisLine: { lineStyle: { color: '#7ed7d0' } } },
            yAxis: { type: 'value', splitLine: { lineStyle: { color: 'rgba(126,215,208,.16)' } } },
            series: [{
                name: seriesName,
                type: 'line',
                smooth: true,
                data: y,
                symbolSize: 9,
                lineStyle: { width: 4, color: '#7ed7d0' },
                itemStyle: { color: '#ef6f5e' },
                areaStyle: { color: 'rgba(126,215,208,.16)' }
            }]
        });
    }

    return { bar: bar, pie: pie, line: line };
})();
