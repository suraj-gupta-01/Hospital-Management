import React, { useState } from "react";
import UploadZone from "../components/UploadZone";
import PrescriptionList from "../components/PrescriptionList";
import { Toaster } from "@/components/ui/sonner";

const Home = () => {
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleUploadSuccess = () => {
    setRefreshTrigger((prev) => prev + 1);
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <h1 className="text-3xl font-semibold text-slate-900">Prescription OCR</h1>
          <p className="text-slate-600 mt-1">Upload handwritten prescriptions for automatic text extraction</p>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Upload Section */}
          <div>
            <UploadZone onUploadSuccess={handleUploadSuccess} />
          </div>

          {/* Results Section */}
          <div>
            <PrescriptionList refreshTrigger={refreshTrigger} />
          </div>
        </div>
      </main>

      <Toaster position="top-right" />
    </div>
  );
};

export default Home;
