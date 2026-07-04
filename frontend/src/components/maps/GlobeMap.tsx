import React, { useRef, useEffect, useState } from 'react';
import Globe from 'react-globe.gl';

export interface GlobeData {
	lat: number;
	lng: number;
	size: number;
	color: string;
	name: string;
	display_type?: string;
	geo_coordinates?: {
		end_lat?: number;
		end_lng?: number;
		[key: string]: any;
	};
}

interface GlobeMapProps {
	data: GlobeData[];
	styleMode?: 'industrial' | 'cyber' | 'ghost';
	onSelect?: (name: string) => void;
}

export const GlobeMap: React.FC<GlobeMapProps> = ({ data, styleMode = 'cyber', onSelect }) => {
	const globeRef = useRef<any>();
	const [dimensions, setDimensions] = useState({ width: window.innerWidth, height: window.innerHeight });

	// 1. FLOW & COMPARISON (飞线层)
	const arcsData = data.filter(d => (d.display_type === 'FLOW' || d.display_type === 'COMPARISON') && d.geo_coordinates?.end_lat).map(d => ({
		startLat: d.lat,
		startLng: d.lng,
		endLat: d.geo_coordinates?.end_lat,
		endLng: d.geo_coordinates?.end_lng,
		color: d.color,
		name: d.name,
		isDynamic: d.display_type === 'FLOW'
	}));

	// 2. RIPPLE & HOTSPOT (波纹层)
	const ringsData = data.filter(d => d.display_type === 'RIPPLE' || d.display_type === 'HOTSPOT').map(d => ({
		lat: d.lat,
		lng: d.lng,
		maxR: (d.size + 1) * 8,
		propagationSpeed: d.display_type === 'HOTSPOT' ? 1 : 2.5,
		repeatPeriod: d.display_type === 'HOTSPOT' ? 1200 : 2000,
		color: d.color
	}));

	// 3. SHIELD_UP (路径/光墙层)
	const pathsData = data.filter(d => d.display_type === 'SHIELD_UP').map(d => [
		[d.lat - 1, d.lng], [d.lat + 1, d.lng]
	]);

	// 4. ZONE (区域/多边形层)
	const polygonsData = data.filter(d => d.display_type === 'ZONE').map(d => ({
		coords: [
			[d.lat - 2, d.lng - 2], [d.lat + 2, d.lng - 2],
			[d.lat + 2, d.lng + 2], [d.lat - 2, d.lng + 2],
			[d.lat - 2, d.lng - 2]
		],
		color: d.color,
		name: d.name
	}));

	// 5. MARKER & Others (基础点层 - 确保所有带波纹或热点的中心点也可点击)
	const pointsData = data.filter(d => 
		d.display_type === 'MARKER' || 
		d.display_type === 'RIPPLE' || 
		d.display_type === 'HOTSPOT' || 
		!d.display_type
	);

	const getGlobeConfig = () => {
		switch (styleMode) {
			case 'cyber':
				return {
					image: "//unpkg.com/three-globe/example/img/earth-night.jpg",
					atmosphere: "#8b5cf6",
					showAtmosphere: true,
					arcDashGap: 0.1,
					arcDashAnimateTime: 2000
				};
			case 'ghost':
				return {
					image: "//unpkg.com/three-globe/example/img/earth-topology.png",
					color: "#1e293b",
					atmosphere: "#64748b",
					showAtmosphere: false,
					arcDashGap: 0.5,
					arcDashAnimateTime: 4000
				};
			case 'industrial':
			default:
				return {
					image: "//unpkg.com/three-globe/example/img/earth-blue-marble.jpg",
					atmosphere: "#3b82f6",
					showAtmosphere: true,
					arcDashGap: 0.2,
					arcDashAnimateTime: 3000
				};
		}
	};

	const config = getGlobeConfig();

	useEffect(() => {
		const handleResize = () => setDimensions({ width: window.innerWidth, height: window.innerHeight });
		window.addEventListener('resize', handleResize);
		return () => window.removeEventListener('resize', handleResize);
	}, []);

	useEffect(() => {
		if (globeRef.current) {
			const controls = globeRef.current.controls();
			controls.autoRotate = true;
			controls.autoRotateSpeed = 0.2;
			controls.enableDamping = true;
		}
	}, []);

	return (
		<div className="absolute inset-0 bg-autoprism-dark overflow-hidden pointer-events-auto">
			<Globe
				ref={globeRef}
				width={dimensions.width}
				height={dimensions.height}
				globeImageUrl={config.image}
				globeColor={config.color}
				atmosphereColor={config.atmosphere}
				showAtmosphere={config.showAtmosphere}
				bumpImageUrl="//unpkg.com/three-globe/example/img/earth-topology.png"
				backgroundImageUrl="//unpkg.com/three-globe/example/img/night-sky.png"

				pointsData={pointsData}
				pointLat="lat"
				pointLng="lng"
				pointColor="color"
				pointAltitude={0.1}
				pointRadius={0.5}
				pointLabel="name"
				onPointClick={(p: any) => onSelect?.(p.name)}

				arcsData={arcsData}
				arcColor="color"
				arcDashLength={(d: any) => d.isDynamic ? 0.4 : 1}
				arcDashGap={(d: any) => d.isDynamic ? config.arcDashGap : 0}
				arcDashAnimateTime={(d: any) => d.isDynamic ? config.arcDashAnimateTime : 0}
				arcStroke={(d: any) => d.isDynamic ? 0.3 : 0.5}
				onArcClick={(a: any) => onSelect?.(a.name)}

				ringsData={ringsData}
				ringColor={(d: any) => d.color}
				ringMaxRadius="maxR"
				ringPropagationSpeed="propagationSpeed"
				ringRepeatPeriod="repeatPeriod"

				pathsData={data.filter(d => d.display_type === 'SHIELD_UP').map(d => ({
					path: [[d.lat - 1, d.lng], [d.lat + 1, d.lng]],
					color: d.color,
					name: d.name
				}))}
				pathPoints={d => d.path}
				pathColor={d => d.color}
				pathStroke={3}
				onPathClick={(p: any) => onSelect?.(p.name)}

				polygonsData={polygonsData}
				polygonAltitude={0.01}
				polygonCapColor={(d: any) => `${d.color}44`}
				polygonSideColor={(d: any) => `${d.color}22`}
				polygonStrokeColor={(d: any) => d.color}
				polygonLabel={(d: any) => d.name}
				onPolygonClick={(p: any) => onSelect?.(p.name)}

				pointsMerge={false}
				pointResolution={32}
			/>
		</div>
	);
};
