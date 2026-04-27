import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const API_BASE_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/ws';

function App() {
  const [recentFrauds, setRecentFrauds] = useState([]);
  const [totalFrauds, setTotalFrauds] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  const [searchId, setSearchId] = useState('');
  const [searchedTransactions, setSearchedTransactions] = useState(null);
  const [isSearching, setIsSearching] = useState(false);

  const [liveTransactions, setLiveTransactions] = useState([]);
  const [wsStatus, setWsStatus] = useState('Bağlanıyor...');

  useEffect(() => {
    fetchFraudData();
    const interval = setInterval(fetchFraudData, 5000);

    const ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      setWsStatus('Bağlı');
    };

    ws.onmessage = (event) => {
      try {
        const newData = JSON.parse(event.data);
        setLiveTransactions((prev) => [newData, ...prev].slice(0, 50));
      } catch (err) {
        console.error("Gelen veri parse edilemedi:", err);
      }
    };

    ws.onerror = (error) => {
      setWsStatus('Hata');
    };

    ws.onclose = () => {
      setWsStatus('Koptu');
    };

    return () => {
      clearInterval(interval);
      ws.close();
    };
  }, []);

  const fetchFraudData = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/frauds?hours=24`);
      setRecentFrauds(response.data.frauds);
      setTotalFrauds(response.data.total_frauds_found);
      setIsLoading(false);
    } catch (error) {
      console.error("API Error:", error);
      setIsLoading(false);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchId) return;
    
    setIsSearching(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/transactions/${searchId}`);
      let safeData = [];
      if (Array.isArray(response.data)) safeData = response.data;
      else if (response.data && Array.isArray(response.data.history)) safeData = response.data.history;
      else if (response.data && Array.isArray(response.data.transactions)) safeData = response.data.transactions;
      else if (response.data && typeof response.data === 'object') safeData = [response.data];
      
      setSearchedTransactions(safeData);
    } catch (error) {
      setSearchedTransactions([]);
    } finally {
      setIsSearching(false);
    }
  };

  const chartData = recentFrauds.map(fraud => ({
    saat: new Date(fraud.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    Tutar: fraud.amount || 0,
    id: fraud.user_id
  })).reverse();

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 font-sans selection:bg-blue-100">
      
      {/* HEADER */}
      <header className="bg-white border-b border-slate-200 shadow-sm sticky top-0 z-50">
        <div className="container mx-auto px-6 py-4 flex flex-col sm:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="bg-blue-600 p-2 rounded-lg">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
            </div>
            <h1 className="text-xl font-extrabold tracking-tight text-slate-900">
              <span className="text-blue-600">FRAUD RADAR</span>
            </h1>
          </div>
          
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-4 py-2 bg-red-50 border border-red-100 rounded-full">
              <span className="relative flex h-3 w-3">
                {totalFrauds > 0 && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>}
                <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
              </span>
              <span className="text-sm font-medium text-red-700">24 Saat: <span className="font-bold">{totalFrauds} Fraud</span></span>
            </div>
            <div className="flex items-center gap-2 px-4 py-2 bg-slate-100 border border-slate-200 rounded-full">
               <span className={`h-2 w-2 rounded-full ${wsStatus === 'Bağlı' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]' : 'bg-slate-400'}`}></span>
              <span className="text-sm font-medium text-slate-600">Sistem: {wsStatus}</span>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-6 py-8">
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
          
          {/* SOL KOLON (Geniş) */}
          <div className="xl:col-span-2 space-y-8">
            
            {/* GRAFİK KARTI */}
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 transition-all hover:shadow-md">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-bold text-slate-800">Risk Analizi (Tutar / Zaman)</h2>
              </div>
              <div className="h-72 w-full">
                {recentFrauds.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                      <XAxis dataKey="saat" tick={{fill: '#94a3b8', fontSize: 12}} tickLine={false} axisLine={false} />
                      <YAxis tick={{fill: '#94a3b8', fontSize: 12}} tickLine={false} axisLine={false} />
                      <Tooltip 
                        cursor={{fill: '#f8fafc'}} 
                        contentStyle={{borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)'}}
                        labelStyle={{fontWeight: 'bold', color: '#0f172a', marginBottom: '4px'}}
                      />
                      <Bar dataKey="Tutar" fill="#ef4444" radius={[6, 6, 0, 0]} maxBarSize={50} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-slate-400 bg-slate-50/50 rounded-xl border border-dashed border-slate-200">
                    <svg className="w-10 h-10 mb-2 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>
                    <span>Yeterli anomali verisi yok</span>
                  </div>
                )}
              </div>
            </div>
            
            {/* KULLANICI SORGULAMA KARTI */}
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 transition-all hover:shadow-md">
              <h2 className="text-lg font-bold mb-5 text-slate-800">Derinlemesine Kullanıcı Analizi</h2>
              
              <form onSubmit={handleSearch} className="flex gap-3 mb-6">
                <div className="relative flex-1">
                  <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
                    <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
                  </div>
                  <input 
                    type="number" 
                    value={searchId}
                    onChange={(e) => setSearchId(e.target.value)}
                    placeholder="Kullanıcı ID (Örn: 1)" 
                    className="block w-full pl-10 pr-3 py-3 bg-slate-50 border border-slate-200 text-slate-900 text-sm rounded-xl focus:ring-2 focus:ring-blue-100 focus:border-blue-500 outline-none transition-all"
                    required
                  />
                </div>
                <button 
                  type="submit" 
                  disabled={isSearching}
                  className="text-white bg-slate-900 hover:bg-slate-800 focus:ring-4 focus:ring-slate-200 font-medium rounded-xl text-sm px-6 py-3 outline-none transition-all disabled:opacity-50"
                >
                  {isSearching ? 'İnceleniyor...' : 'Sorgula'}
                </button>
              </form>

              <div className="h-56 overflow-y-auto pr-2 custom-scrollbar">
                {!searchedTransactions ? (
                  <div className="h-full flex items-center justify-center text-slate-400 text-sm">
                    Kullanıcının işlem sabıka kaydını görmek için ID girin.
                  </div>
                ) : searchedTransactions.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-slate-500 bg-slate-50 rounded-xl">
                    <span className="text-2xl mb-2">🍃</span>
                    <span className="text-sm">Bu kullanıcı tertemiz. İşlem bulunamadı.</span>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {Array.isArray(searchedTransactions) && searchedTransactions.map((tx, index) => (
                      <div key={tx.id || index} className={`p-4 rounded-xl border text-sm flex justify-between items-center transition-colors ${tx.is_fraud ? 'bg-red-50/50 border-red-100 hover:bg-red-50' : 'bg-emerald-50/50 border-emerald-100 hover:bg-emerald-50'}`}>
                        <div>
                          {tx.amount !== undefined ? (
                            <>
                              <div className="font-bold text-slate-800 text-base">{tx.amount.toLocaleString('tr-TR')} ₺</div>
                              {tx.timestamp && <div className="text-xs text-slate-500 mt-0.5 font-medium">{new Date(tx.timestamp).toLocaleString('tr-TR')}</div>}
                            </>
                          ) : (
                            <div className="text-xs font-mono text-slate-500">Geçersiz Veri Formatı</div>
                          )}
                        </div>
                        <div className={`px-3 py-1.5 rounded-md text-[11px] font-bold tracking-wide uppercase ${tx.is_fraud ? 'bg-red-100 text-red-700' : 'bg-emerald-100 text-emerald-700'}`}>
                          {tx.is_fraud ? 'Kural İhlali' : 'Temiz'}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* SAĞ KOLON (Dar) */}
          <div className="space-y-8">
            
            {/* ANLIK FRAUD UYARILARI */}
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 border-t-4 border-t-red-500 flex flex-col h-[400px]">
              <h2 className="text-lg font-bold mb-4 text-slate-800 flex items-center gap-2">
                <svg className="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
                Radar Uyarıları
              </h2>
              <div className="overflow-y-auto pr-2 space-y-3 flex-1 custom-scrollbar">
                {isLoading ? (
                  <div className="h-full flex items-center justify-center text-slate-400 animate-pulse text-sm">Radarlar taranıyor...</div>
                ) : recentFrauds.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-emerald-600/70 text-sm">
                    <svg className="w-12 h-12 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                    <span>Şu an her şey güvenli.</span>
                  </div>
                ) : (
                  recentFrauds.map((fraud) => (
                    <div key={fraud.id} className="bg-white p-4 rounded-xl border border-red-100 shadow-[0_2px_10px_-3px_rgba(239,68,68,0.1)] relative overflow-hidden">
                      <div className="absolute top-0 left-0 w-1 h-full bg-red-500"></div>
                      <div className="flex justify-between items-start mb-1">
                        <span className="font-bold text-slate-800 text-sm">User ID: <span className="text-red-600">{fraud.user_id}</span></span>
                        <span className="text-slate-400 text-[10px] font-medium">{new Date(fraud.timestamp).toLocaleTimeString('tr-TR')}</span>
                      </div>
                      <div className="text-slate-900 font-extrabold text-lg mb-2">{fraud.amount.toLocaleString('tr-TR')} ₺</div>
                      <div className="text-slate-600 text-[11px] leading-relaxed bg-slate-50 p-2 rounded border border-slate-100">
                        <span className="font-semibold text-slate-700">İhlal:</span> {fraud.fraud_reasons}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* WEBSOCKET CANLI AKIŞ */}
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex flex-col h-[350px] relative overflow-hidden">
               {/* Arka plan süsü */}
               <div className="absolute -right-6 -top-6 w-24 h-24 bg-blue-50 rounded-full opacity-50 blur-xl"></div>
              
              <div className="flex justify-between items-center mb-4 relative z-10">
                <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                  <svg className="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                  Canlı Akış
                </h2>
                
                {/* YENİ EKLENEN CANLI BAĞLANTI İKONU */}
                <div className="flex items-center gap-2 bg-slate-50 px-2.5 py-1 rounded-full border border-slate-200">
                  <span className="relative flex h-2 w-2">
                    {wsStatus === 'Bağlı' && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>}
                    <span className={`relative inline-flex rounded-full h-2 w-2 ${wsStatus === 'Bağlı' ? 'bg-emerald-500' : 'bg-slate-400'}`}></span>
                  </span>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    {wsStatus === 'Bağlı' ? 'Canlı' : 'Bekleniyor'}
                  </span>
                </div>
              </div>
              <div className="overflow-y-auto pr-2 space-y-2.5 flex-1 custom-scrollbar relative z-10">
                {liveTransactions.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-slate-400 text-sm">
                    <span className="animate-pulse">İşlemler dinleniyor...</span>
                  </div>
                ) : (
                  liveTransactions.map((tx, index) => (
                    <div key={index} className={`p-3 rounded-lg border text-sm flex justify-between items-center transition-all ${tx.is_fraud ? 'bg-red-50 border-red-200' : 'bg-white border-slate-100 hover:border-slate-300'}`}>
                      <div>
                        <div className="font-semibold text-slate-700 text-[13px]">
                          User: <span className="text-slate-900">{tx.user_id || '?'}</span>
                        </div>
                        <div className="font-bold text-slate-900 mt-0.5">{tx.amount || '?'} ₺</div>
                      </div>
                      <div className="flex flex-col items-end">
                         {tx.is_fraud ? (
                            <span className="text-red-600 text-[10px] font-bold px-2 py-1 bg-red-100 rounded uppercase tracking-wider mb-1">Fraud</span>
                         ) : (
                            <span className="text-emerald-500 text-[10px] font-bold px-2 py-1 bg-emerald-50 rounded uppercase tracking-wider mb-1">Pass</span>
                         )}
                        <div className="text-[10px] text-slate-400 font-medium">{new Date().toLocaleTimeString('tr-TR')}</div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

          </div>
        </div>
      </main>

      {/* FOOTER */}
      <footer className="border-t border-slate-200 mt-auto py-6 bg-white text-center text-slate-500 text-sm">
        <p>Fraud Detection Platform &copy; 2026</p>
      </footer>

    </div>
  );
}

export default App;