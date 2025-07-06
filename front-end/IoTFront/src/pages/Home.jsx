import React from 'react';

export default function Home() {
  return (
    <div>
      <section className="bg-gray-50 py-16 px-4">
        <div className="container mx-auto grid md:grid-cols-2 gap-12 items-center">
          <div>
            <h1 className="text-4xl md:text-5xl font-bold mb-6">
              How Air Pollution{" "}
              <span className="text-blue-400">Can Shortens</span>{" "}
              <span className="text-blue-400">Your Life</span>
            </h1>
            <p className="text-gray-600 text-lg mb-8 leading-relaxed">
              Pollution is nothing but the resources we are not harvesting. We
              allow them to disperse because we've been ignorant of their value.
            </p>
          </div>

          <div className="flex justify-center">
            <div className="w-80 h-80 bg-gray-400 rounded-full relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-b from-gray-300 to-gray-500">
                {/* Industrial illustration placeholder */}
                <div className="absolute bottom-0 left-1/2 transform -translate-x-1/2">
                  <div className="flex items-end space-x-2">
                    {/* Factory buildings */}
                    <div className="w-12 h-16 bg-orange-500 rounded-t"></div>
                    <div className="w-10 h-12 bg-red-500 rounded-t"></div>
                    <div className="w-8 h-20 bg-orange-600 rounded-t"></div>
                    <div className="w-6 h-24 bg-red-600 rounded-t"></div>
                  </div>
                  {/* Smoke stacks */}
                  <div className="flex justify-center space-x-4 -mt-2">
                    <div className="w-2 h-16 bg-gray-600"></div>
                    <div className="w-2 h-20 bg-gray-700"></div>
                    <div className="w-2 h-18 bg-gray-600"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
