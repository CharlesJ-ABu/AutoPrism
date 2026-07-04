import React, { useState, useEffect } from 'react';
import DeckGL from '@deck.gl/react';
import { ScatterplotLayer, GeoJsonLayer, BitmapLayer, ArcLayer, PathLayer } from '@deck.gl/layers';
import { TileLayer } from '@deck.gl/geo-layers';

export interface DeckGLData {
	position: [number, number];
	size: number;
	color: [number, number, number];
	name: string;
	display_type?: string;
	geo_coordinates?: {
		end_lat?: number;
		end_lng?: number;
		[key: string]: any;
	};
}

interface DeckGLMapProps {
	data: DeckGLData[];
	styleMode?: 'industrial' | 'cyber' | 'ghost';
	onSelect?: (name: string) => void;
}

const INITIAL_VIEW_STATE = {
	longitude: 104.1954,
	latitude: 35.8617,
	zoom: 3,
	maxZoom: 16,
	pitch: 0, // 恢复纯俯视视角
	bearing: 0
};

export const DeckGLMap: React.FC<DeckGLMapProps> = ({ data, styleMode = 'cyber', onSelect }) => {
	const [viewState, setViewState] = useState(INITIAL_VIEW_STATE);
	const [geoData, setGeoData] = useState<any>(null);

	const getMapColors = () => {
		switch (styleMode) {
			case 'cyber':
				return {
					tile: 'https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png',
					fill: [139, 92, 246, 30],
					line: [139, 92, 246, 200],
					bg: '#000000'
				};
			case 'ghost':
				return {
					tile: 'https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png',
					fill: [100, 116, 139, 30],
					line: [100, 116, 139, 120],
					bg: '#020617'
				};
			case 'industrial':
			default:
				return {
					tile: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
					fill: [15, 15, 35, 100],
					line: [255, 255, 255, 50],
					bg: '#0F0F23'
				};
		}
	};

	const colors = getMapColors();

	useEffect(() => {
		fetch('https://raw.githubusercontent.com/datasets/geo-boundaries-world-110m/master/countries.geojson')
			.then(res => res.json())
			.then(json => setGeoData(json))
			.catch(err => console.error("Failed to load map data", err));
	}, []);

	// 数据过滤层级
	const scatterData = data.filter(d => 
		!d.display_type || 
		d.display_type === 'MARKER' || 
		d.display_type === 'HOTSPOT' || 
		d.display_type === 'RIPPLE' || 
		d.display_type === 'ZONE'
	);
	const arcData = data.filter(d => (d.display_type === 'FLOW' || d.display_type === 'COMPARISON') && d.geo_coordinates?.end_lat);
	const pathData = data.filter(d => d.display_type === 'SHIELD_UP').map(d => ({
		path: [[d.position[0] - 1, d.position[1]], [d.position[0] + 1, d.position[1]]],
		color: d.color,
		name: d.name
	}));

	const layers = [
		new TileLayer({
			id: 'tile-layer',
			data: colors.tile,
			minZoom: 0,
			maxZoom: 19,
			tileSize: 256,
			renderSubLayers: (props: any) => {
				const { bbox: { west, south, east, north } } = props.tile;
				return new BitmapLayer(props, {
					data: null,
					image: props.data,
					bounds: [west, south, east, north]
				});
			}
		}),
		new GeoJsonLayer({
			id: 'base-map',
			data: geoData,
			stroked: true,
			filled: true,
			lineWidthMinPixels: 1,
			getLineColor: colors.line as any,
			getFillColor: colors.fill as any,
		}),
		// 飞线层 (FLOW / COMPARISON)
		new ArcLayer({
			id: 'arc-layer',
			data: arcData,
			pickable: true,
			getWidth: 3,
			getSourcePosition: (d: any) => d.position,
			getTargetPosition: (d: any) => [d.geo_coordinates.end_lng, d.geo_coordinates.end_lat],
			getSourceColor: (d: any) => d.color,
			getTargetColor: (d: any) => [255, 255, 255, 120],
			onClick: (info: any) => info.object && onSelect?.(info.object.name)
		}),
		// 路径层 (SHIELD_UP)
		new PathLayer({
			id: 'path-layer',
			data: pathData,
			pickable: true,
			getPath: (d: any) => d.path,
			getColor: (d: any) => d.color,
			getWidth: 5,
			widthMinPixels: 8,
			onClick: (info: any) => info.object && onSelect?.(info.object.name)
		}),
		// 基础散点/热点层 (处理 ZONE, HOTSPOT 等)
		new ScatterplotLayer({
			id: 'scatterplot-layer',
			data: scatterData,
			pickable: true,
			autoHighlight: true, // 增加 Hover 高亮
			highlightColor: [255, 255, 255, 100],
			opacity: 0.8,
			stroked: true,
			filled: true,
			radiusScale: 1,
			radiusMinPixels: 3.5,
			radiusMaxPixels: 100,
			lineWidthMinPixels: 1,
			getPosition: (d: any) => d.position,
			getFillColor: (d: any) => d.color,
			getLineColor: (d: any) => [255, 255, 255, 150],
			getRadius: (d: any) => Math.sqrt(d.size) * 800,
			onClick: (info: any) => info.object && onSelect?.(info.object.name)
		})
	];

	return (
		<div className="absolute inset-0 pointer-events-auto" style={{ backgroundColor: colors.bg }}>
			<DeckGL
				layers={layers}
				initialViewState={viewState}
				controller={true}
				onViewStateChange={(e: any) => setViewState(e.viewState)}
				getTooltip={({ object }) => object && (object.name || object.properties?.name)}
			/>
		</div>
	);
};
