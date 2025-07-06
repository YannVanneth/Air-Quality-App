import React from 'react';
import pollutionImage from './assets/air-pollution.png';
import "./App.css";

const pollutionAspects = [
    {
        icon: '❤️',
        title: "Human Health",
        description: "Air pollution causes breathing problems like asthma and lung infections. It can also lead to heart diseases, strokes, and even cancer.",
        stats: "7 million premature deaths annually",
        color: "bg-rose-100",
        textColor: "text-rose-600"
    },
    {
        icon: '🌱',
        title: "Environment",
        description: "Acid rain, greenhouse gases, and ozone layer depletion are contributing to climate change by causing harm to plants, soil, and water bodies.",
        stats: "1.5°C global temperature rise since 1880",
        color: "bg-emerald-100",
        textColor: "text-emerald-600"
    },
    {
        icon: '💰',
        title: "Economy",
        description: "High pollution levels increase healthcare costs, lead to increased hospital visits, and negatively impact workers' productivity, crop yields, food production, and trade.",
        stats: "$5 trillion annual economic losses",
        color: "bg-amber-100",
        textColor: "text-amber-600"
    },
    {
        icon: '🐾',
        title: "Wildlife",
        description: "Air and water pollution affects animals' health and survival, while climate change disrupts natural habitats, forcing species to migrate or face extinction.",
        stats: "1 million species at risk of extinction",
        color: "bg-indigo-100",
        textColor: "text-indigo-600"
    },
];

function App() {
    return (
        <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white">
            {/* Hero Section */}
            <section className="relative p-24 px-4 sm:px-6 lg:px-8 overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 to-teal-500/10 transform -skew-y-3 origin-top-left"></div>

                <div className="container mx-auto relative z-10">
                    <div className="flex flex-col lg:flex-row items-center gap-12">
                        <div className="lg:w-1/2 text-center lg:text-left">
                            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight mb-6">
                                <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-teal-600">How Air Pollution</span>
                                <br />
                                <span className="text-transparent bg-clip-text bg-gradient-to-r from-teal-600 to-emerald-600">Shortens Your Life</span>
                            </h1>
                            <p className="text-lg text-gray-700 max-w-lg mx-auto lg:mx-0 mb-8">
                                Pollution is nothing but the resources we are not harvesting. We allow them to disperse because we've been ignorant of their value.
                            </p>
                            <div className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start">
                                <button className="px-6 py-3 bg-gradient-to-r from-blue-600 to-teal-600 text-white rounded-lg shadow-md hover:shadow-lg transition-all">
                                    Learn More
                                </button>
                                <button className="px-6 py-3 border-2 border-blue-600 text-blue-600 rounded-lg hover:bg-blue-50 transition-all">
                                    Take Action
                                </button>
                            </div>
                        </div>
                        <div className="lg:w-1/2 mt-12 lg:mt-0">
                            <div className="relative rounded-2xl transform hover:scale-[1.02] transition-transform">
                                <img
                                    src={pollutionImage}
                                    alt="Air pollution impact illustration"
                                    className="w-full h-auto rounded-full"
                                />
                                {/*<div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent"></div>*/}
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Impact Cards Section */}
            <section className="py-20 px-4 sm:px-6 lg:px-8">
                <div className="container mx-auto flex flex-col">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl lg:text-4xl font-bold text-gray-900 mb-4">
                            Air Pollution Affects Multiple Aspects Of Life
                        </h2>
                        <div className="w-20 h-1.5 bg-gradient-to-r from-blue-400 to-teal-400 mx-auto mb-6"></div>
                        <p className="text-lg text-gray-600 max-w-3xl mx-auto">
                            Air pollution harms health, damages the environment, affects the economy, and disrupts wildlife.
                        </p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                        {pollutionAspects.map((aspect, index) => (
                            <div
                                key={index}
                                className={`group rounded-xl overflow-hidden shadow-md hover:shadow-xl transition-all duration-300 hover:-translate-y-2 ${aspect.color}`}
                            >
                                <div className="p-6">
                                    <div className={`text-4xl mb-4 ${aspect.textColor}`}>{aspect.icon}</div>
                                    <h3 className={`text-xl font-bold mb-3 ${aspect.textColor}`}>{aspect.title}</h3>
                                    <p className="text-gray-700 mb-4">{aspect.description}</p>
                                    <div className="text-sm font-medium text-gray-500">
                                        {aspect.stats}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>
        </div>
    );
}

export default App;