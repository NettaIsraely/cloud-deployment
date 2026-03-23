import { useCallback, useEffect, useState } from "react";
import { apiUrl } from "./api";
import { ToastContainer, useToasts } from "./Toast";

const USER_STORAGE_KEY = "tlvflow_user";
const DEFAULT_LAT = 32.0853;
const DEFAULT_LON = 34.7818;
const END_RIDE_STATION_THRESHOLD_M = 5;
const START_RIDE_STATION_THRESHOLD_M = 5;

function haversineDistanceMetres(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  const R = 6371000;
  const φ1 = (lat1 * Math.PI) / 180;
  const φ2 = (lat2 * Math.PI) / 180;
  const Δφ = ((lat2 - lat1) * Math.PI) / 180;
  const Δλ = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(Δφ / 2) ** 2 +
    Math.cos(φ1) * Math.cos(φ2) * Math.sin(Δλ / 2) ** 2;
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

type View =
  | "auth"
  | "home"
  | "findStation"
  | "startRide"
  | "endRide"
  | "profile"
  | "rideHistory"
  | "upgradePro"
  | "reportVehicle";

interface User {
  user_id: string;
  name: string;
  is_pro: boolean;
}

interface ActiveRide {
  ride_id: string;
  vehicle_id: string;
}

function formatErrorDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item: { msg?: string; loc?: unknown[] }) => {
        const msg = item?.msg ?? "Validation error";
        const loc = Array.isArray(item?.loc) ? item.loc.join(" ") : "";
        return loc ? `${loc}: ${msg}` : msg;
      })
      .join("\n");
  }
  return String(detail);
}

function loadUser(): User | null {
  try {
    const raw = sessionStorage.getItem(USER_STORAGE_KEY);
    if (!raw) return null;
    const u = JSON.parse(raw) as User;
    return u?.user_id && u?.name !== undefined && typeof u?.is_pro === "boolean"
      ? u
      : null;
  } catch {
    return null;
  }
}

function saveUser(user: User | null) {
  if (user) sessionStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
  else sessionStorage.removeItem(USER_STORAGE_KEY);
}

function App() {
  const { toasts, add: addToast, remove: removeToast } = useToasts();
  const [user, setUser] = useState<User | null>(loadUser);
  const [view, setView] = useState<View>(() =>
    loadUser() ? "home" : "auth"
  );
  const [activeRide, setActiveRide] = useState<ActiveRide | null>(null);

  const fetchActiveRide = useCallback(async (userId: string) => {
    try {
      const res = await fetch(
        apiUrl(`/ride/rides/active?user_id=${encodeURIComponent(userId)}`)
      );
      if (res.ok) {
        const data = await res.json();
        setActiveRide({ ride_id: data.ride_id, vehicle_id: data.vehicle_id });
      } else {
        setActiveRide(null);
      }
    } catch {
      setActiveRide(null);
    }
  }, []);

  useEffect(() => {
    if (user?.user_id) fetchActiveRide(user.user_id);
    else setActiveRide(null);
  }, [user?.user_id, fetchActiveRide]);

  useEffect(() => {
    if (user) saveUser(user);
  }, [user]);

  // Auth
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [loginError, setLoginError] = useState<string | null>(null);
  const [signupName, setSignupName] = useState("");
  const [signupEmail, setSignupEmail] = useState("");
  const [signupPassword, setSignupPassword] = useState("");
  const [signupPaymentId, setSignupPaymentId] = useState("");
  const [signupError, setSignupError] = useState<string | null>(null);
  const [authTab, setAuthTab] = useState<"login" | "signup">("login");

  const doLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError(null);
    try {
      const res = await fetch(apiUrl("/login"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: loginEmail, password: loginPassword }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(formatErrorDetail(data.detail ?? data));
      setUser({
        user_id: data.user_id,
        name: data.name,
        is_pro: data.is_pro ?? false,
      });
      setView("home");
    } catch (err) {
      setLoginError(err instanceof Error ? err.message : String(err));
    }
  };

  const doSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setSignupError(null);
    const body = {
      name: signupName,
      email: signupEmail,
      password: signupPassword,
      payment_method_id: signupPaymentId.trim(),
    };
    try {
      const reg = await fetch(apiUrl("/register"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const regData = await reg.json();
      if (!reg.ok) throw new Error(formatErrorDetail(regData.detail ?? regData));
      const loginRes = await fetch(apiUrl("/login"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: signupEmail, password: signupPassword }),
      });
      const loginData = await loginRes.json();
      if (!loginRes.ok) {
        setUser({ user_id: regData.user_id, name: signupName, is_pro: false });
      } else {
        setUser({
          user_id: loginData.user_id,
          name: loginData.name,
          is_pro: loginData.is_pro ?? false,
        });
      }
      setView("home");
    } catch (err) {
      setSignupError(err instanceof Error ? err.message : String(err));
    }
  };

  // Find nearest station
  const [nearestResult, setNearestResult] = useState<{
    station_id: number;
    name: string;
    lat: number;
    lon: number;
    capacity: number;
    available_slots: number;
    is_full: boolean;
    is_empty: boolean;
  } | null>(null);
  const [nearestError, setNearestError] = useState<string | null>(null);

  const findNearest = useCallback(async (lat: number, lon: number) => {
    setNearestError(null);
    setNearestResult(null);
    try {
      const res = await fetch(apiUrl(`/stations/nearest?lat=${lat}&lon=${lon}`));
      const data = await res.json();
      if (!res.ok) throw new Error(formatErrorDetail(data.detail ?? data));
      setNearestResult(data);
    } catch (err) {
      setNearestError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  const useMyLocation = () => {
    if (!navigator.geolocation) {
      findNearest(DEFAULT_LAT, DEFAULT_LON);
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => findNearest(pos.coords.latitude, pos.coords.longitude),
      () => findNearest(DEFAULT_LAT, DEFAULT_LON)
    );
  };

  // Start ride: location-based (nearest station, within 5 m) with manual lat/lon fallback
  const [startNearestStation, setStartNearestStation] = useState<{
    station_id: number;
    name: string;
    lat: number;
    lon: number;
    distance_m: number;
  } | null>(null);
  const [startUserPosition, setStartUserPosition] = useState<{
    lat: number;
    lon: number;
  } | null>(null);
  const [startLocationLoading, setStartLocationLoading] = useState(false);
  const [startManualLat, setStartManualLat] = useState("");
  const [startManualLon, setStartManualLon] = useState("");
  const [startError, setStartError] = useState<string | null>(null);
  const [startSubmitLoading, setStartSubmitLoading] = useState(false);

  const loadStartRideNearest = useCallback(
    async (lat: number, lon: number) => {
      if (!user) return;
      setStartError(null);
      setStartNearestStation(null);
      setStartUserPosition(null);
      try {
        const res = await fetch(
          apiUrl(`/stations/nearest?lat=${lat}&lon=${lon}`)
        );
        const data = await res.json();
        if (!res.ok)
          throw new Error(formatErrorDetail(data.detail ?? data));
        const distance_m = haversineDistanceMetres(
          lat,
          lon,
          data.lat,
          data.lon
        );
        setStartUserPosition({ lat, lon });
        setStartNearestStation({
          station_id: data.station_id,
          name: data.name,
          lat: data.lat,
          lon: data.lon,
          distance_m: Math.round(distance_m),
        });
      } catch (err) {
        setStartError(err instanceof Error ? err.message : String(err));
      }
    },
    [user]
  );

  const useMyLocationForStart = useCallback(() => {
    setStartError(null);
    setStartLocationLoading(true);
    const resolve = (): Promise<{ lat: number; lon: number }> =>
      new Promise((resolve) => {
        if (!navigator.geolocation)
          return resolve({ lat: DEFAULT_LAT, lon: DEFAULT_LON });
        navigator.geolocation.getCurrentPosition(
          (p) =>
            resolve({
              lat: p.coords.latitude,
              lon: p.coords.longitude,
            }),
          () => resolve({ lat: DEFAULT_LAT, lon: DEFAULT_LON })
        );
      });
    resolve()
      .then((latLon) => loadStartRideNearest(latLon.lat, latLon.lon))
      .catch(() => setStartError("Location error."))
      .finally(() => setStartLocationLoading(false));
  }, [loadStartRideNearest]);

  const checkManualLocationForStart = (e: React.FormEvent) => {
    e.preventDefault();
    const lat = parseFloat(startManualLat.trim());
    const lon = parseFloat(startManualLon.trim());
    if (Number.isNaN(lat) || Number.isNaN(lon)) {
      setStartError("Enter valid numbers for lat and lon.");
      return;
    }
    setStartLocationLoading(true);
    loadStartRideNearest(lat, lon).finally(() =>
      setStartLocationLoading(false)
    );
  };

  const startAtStation =
    startNearestStation !== null &&
    startNearestStation.distance_m <= START_RIDE_STATION_THRESHOLD_M;

  const doStartRideFromStation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user || !startUserPosition) return;
    setStartError(null);
    setStartSubmitLoading(true);
    try {
      const res = await fetch(apiUrl("/ride/start"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: user.user_id,
          lon: startUserPosition.lon,
          lat: startUserPosition.lat,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(formatErrorDetail(data.detail ?? data));
      setActiveRide({
        ride_id: data.ride_id,
        vehicle_id: data.vehicle_id,
      });
      addToast("success", "Ride started");
      setView("home");
      setStartNearestStation(null);
      setStartUserPosition(null);
      setStartManualLat("");
      setStartManualLon("");
    } catch (err) {
      setStartError(err instanceof Error ? err.message : String(err));
      addToast("error", err instanceof Error ? err.message : String(err));
    } finally {
      setStartSubmitLoading(false);
    }
  };

  useEffect(() => {
    if (view === "startRide") {
      setStartNearestStation(null);
      setStartUserPosition(null);
      setStartError(null);
      useMyLocationForStart();
    }
  }, [view]); // eslint-disable-line react-hooks/exhaustive-deps -- run when entering startRide only

  // End ride: must be at station (within 5 m)
  const [endError, setEndError] = useState<string | null>(null);
  const [endLoading, setEndLoading] = useState(false);
  const [endNearestStation, setEndNearestStation] = useState<{
    station_id: number;
    name: string;
    lat: number;
    lon: number;
    distance_m: number;
  } | null>(null);
  const [endUserPosition, setEndUserPosition] = useState<{
    lat: number;
    lon: number;
  } | null>(null);
  const [endLocationLoading, setEndLocationLoading] = useState(false);
  const [endManualLat, setEndManualLat] = useState("");
  const [endManualLon, setEndManualLon] = useState("");
  const endAtStation =
    endNearestStation !== null &&
    endNearestStation.distance_m <= END_RIDE_STATION_THRESHOLD_M;

  const applyEndLocation = useCallback((lat: number, lon: number) => {
    setEndError(null);
    setEndNearestStation(null);
    setEndUserPosition(null);
    setEndLocationLoading(true);
    fetch(apiUrl(`/stations/nearest?lat=${lat}&lon=${lon}`))
      .then((r) =>
        r.json().then((data: { station_id: number; name: string; lat: number; lon: number }) => ({ ok: r.ok, data }))
      )
      .then(({ ok, data }) => {
        if (!ok) {
          setEndError("Could not find nearest station.");
          setEndLocationLoading(false);
          return;
        }
        const distance_m = haversineDistanceMetres(lat, lon, data.lat, data.lon);
        setEndUserPosition({ lat, lon });
        setEndNearestStation({
          station_id: data.station_id,
          name: data.name,
          lat: data.lat,
          lon: data.lon,
          distance_m: Math.round(distance_m),
        });
        setEndError(null);
      })
      .catch(() => setEndError("Location error."))
      .finally(() => setEndLocationLoading(false));
  }, []);

  const loadEndRideNearest = useCallback(() => {
    if (!user || !activeRide) return;
    setEndError(null);
    setEndNearestStation(null);
    setEndUserPosition(null);
    setEndLocationLoading(true);
    const resolveLocation = (): Promise<{ lat: number; lon: number }> =>
      new Promise((resolve) => {
        if (!navigator.geolocation)
          return resolve({ lat: DEFAULT_LAT, lon: DEFAULT_LON });
        navigator.geolocation.getCurrentPosition(
          (p) =>
            resolve({
              lat: p.coords.latitude,
              lon: p.coords.longitude,
            }),
          () => resolve({ lat: DEFAULT_LAT, lon: DEFAULT_LON })
        );
      });
    resolveLocation().then((latLon) => applyEndLocation(latLon.lat, latLon.lon));
  }, [user, activeRide, applyEndLocation]);

  const useManualEndCoordinates = () => {
    const lat = parseFloat(endManualLat.trim());
    const lon = parseFloat(endManualLon.trim());
    if (Number.isNaN(lat) || Number.isNaN(lon)) {
      setEndError("Enter valid latitude and longitude (numbers).");
      return;
    }
    if (lat < -90 || lat > 90) {
      setEndError("Latitude must be between -90 and 90.");
      return;
    }
    if (lon < -180 || lon > 180) {
      setEndError("Longitude must be between -180 and 180.");
      return;
    }
    setEndError(null);
    applyEndLocation(lat, lon);
  };

  useEffect(() => {
    if (view === "endRide" && activeRide) {
      setEndNearestStation(null);
      setEndUserPosition(null);
      setEndManualLat("");
      setEndManualLon("");
      loadEndRideNearest();
    }
  }, [view, activeRide, loadEndRideNearest]);

  const NOT_IN_STATION_TOAST = "Not in station, cannot end ride.";

  const doEndRide = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user || !activeRide) return;
    if (!endAtStation || !endNearestStation || !endUserPosition) {
      addToast("error", NOT_IN_STATION_TOAST);
      setEndError("You must be within 5 m of a station to end the ride.");
      return;
    }
    setEndError(null);
    setEndLoading(true);
    try {
      const res = await fetch(apiUrl("/ride/end"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ride_id: activeRide.ride_id,
          lon: endUserPosition.lon,
          lat: endUserPosition.lat,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        const detail = typeof data.detail === "string" ? data.detail : String(data.detail ?? "");
        if (detail.toLowerCase().includes("within 5 meters") || detail.toLowerCase().includes("5 meters")) {
          addToast("error", NOT_IN_STATION_TOAST);
          setEndError("You must be within 5 m of a station to end the ride.");
          return;
        }
        throw new Error(formatErrorDetail(data.detail ?? data));
      }
      setActiveRide(null);
      setEndNearestStation(null);
      setEndUserPosition(null);
      setEndManualLat("");
      setEndManualLon("");
      const fee = typeof data.payment_charged === "number" ? data.payment_charged : 0;
      addToast("success", `Ride ended. Payment of ${fee} ILS processed.`);
      setView("home");
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setEndError(msg);
      addToast("error", msg);
    } finally {
      setEndLoading(false);
    }
  };

  // Profile
  const [profile, setProfile] = useState<{
    user_id: string;
    name: string;
    email: string;
    payment_method_id: string;
    is_pro: boolean;
  } | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [newPaymentId, setNewPaymentId] = useState("");
  const [profilePaymentError, setProfilePaymentError] = useState<string | null>(
    null
  );

  // Ride history
  const [rideHistory, setRideHistory] = useState<
    { ride_id: string; vehicle_id: string; start_time: string; end_time: string; fee: number; status: string }[]
  >([]);
  const [rideHistoryError, setRideHistoryError] = useState<string | null>(null);

  function formatRideDateTime(iso: string): string {
    if (!iso) return "—";
    try {
      const d = new Date(iso);
      return d.toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" });
    } catch {
      return iso;
    }
  }


  useEffect(() => {
    if (view !== "rideHistory" || !user) return;
    setRideHistoryError(null);
    fetch(apiUrl(`/ride/rides/history?user_id=${encodeURIComponent(user.user_id)}`))
      .then((r) => r.json())
      .then((data) => {
        if (data.rides) setRideHistory(data.rides);
        else setRideHistoryError("Failed to load ride history");
      })
      .catch(() => setRideHistoryError("Failed to load ride history"));
  }, [view, user?.user_id]);

  // Upgrade to Pro
  const [licenseNumber, setLicenseNumber] = useState("");
  const [licenseExpiry, setLicenseExpiry] = useState("");
  const [licenseImageUrl, setLicenseImageUrl] = useState("");
  const [upgradeError, setUpgradeError] = useState<string | null>(null);
  const [upgradeLoading, setUpgradeLoading] = useState(false);

  const doUpgrade = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user || !licenseNumber.trim() || !licenseExpiry.trim()) return;
    setUpgradeError(null);
    setUpgradeLoading(true);
    try {
      const res = await fetch(apiUrl("/user/upgrade"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: user.user_id,
          license_number: licenseNumber.trim(),
          license_expiry: licenseExpiry.trim(),
          license_image_url: licenseImageUrl.trim() || undefined,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(formatErrorDetail(data.detail ?? data));
      setUser((prev) => (prev ? { ...prev, is_pro: true } : null));
      addToast("success", "Upgraded to Pro");
      setView("home");
      setLicenseNumber("");
      setLicenseExpiry("");
      setLicenseImageUrl("");
    } catch (err) {
      setUpgradeError(err instanceof Error ? err.message : String(err));
    } finally {
      setUpgradeLoading(false);
    }
  };

  // Report degraded: only during active ride
  const [reportError, setReportError] = useState<string | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const reportVehicleId = activeRide?.vehicle_id ?? "";

  const doReport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user || !reportVehicleId.trim()) return;
    setReportError(null);
    setReportLoading(true);
    try {
      const res = await fetch(apiUrl("/vehicle/report-degraded"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: user.user_id,
          vehicle_id: reportVehicleId.trim(),
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(formatErrorDetail(data.detail ?? data));
      addToast("success", "Vehicle reported as degraded");
      setView("home");
      setActiveRide(null);
    } catch (err) {
      setReportError(err instanceof Error ? err.message : String(err));
      addToast("error", err instanceof Error ? err.message : String(err));
    } finally {
      setReportLoading(false);
    }
  };

  useEffect(() => {
    if (view !== "profile" || !user) return;
    setProfileError(null);
    setProfile(null);
    fetch(
      apiUrl(`/users/me?user_id=${encodeURIComponent(user.user_id)}`)
    )
      .then((r) => r.json())
      .then((data) => {
        if (data.user_id) setProfile(data);
        else setProfileError("Failed to load profile");
      })
      .catch(() => setProfileError("Failed to load profile"));
  }, [view, user?.user_id]);

  const updatePaymentMethod = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user || !newPaymentId.trim()) return;
    setProfilePaymentError(null);
    try {
      const res = await fetch(
        apiUrl(`/users/${user.user_id}/payment-method`),
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ payment_method_id: newPaymentId.trim() }),
        }
      );
      if (!res.ok) {
        const data = await res.json();
        throw new Error(formatErrorDetail(data.detail ?? data));
      }
      if (profile)
        setProfile({ ...profile, payment_method_id: newPaymentId.trim() });
      setNewPaymentId("");
      addToast("success", "Payment method updated");
    } catch (err) {
      setProfilePaymentError(
        err instanceof Error ? err.message : String(err)
      );
    }
  };

  const logout = () => {
    setUser(null);
    setActiveRide(null);
    setView("auth");
  };

  useEffect(() => {
    if (!user && view !== "auth") setView("auth");
  }, [user, view]);

  // Auth view
  if (!user && view === "auth") {
    return (
      <>
        <main className="app">
          <div className="card section-card">
            <h1 className="app-title">TLVFlow</h1>
            <p className="app-tagline">Vehicle management</p>
            <div className="view-header" style={{ marginTop: "1rem" }}>
              <button
                type="button"
                className={`view-back ${authTab === "login" ? "" : "muted"}`}
                onClick={() => setAuthTab("login")}
              >
                Login
              </button>
              <button
                type="button"
                className={`view-back ${authTab === "signup" ? "" : "muted"}`}
                onClick={() => setAuthTab("signup")}
              >
                Sign up
              </button>
            </div>
            {authTab === "login" && (
              <form onSubmit={doLogin} className="form">
                <label className="form-row">
                  <span>Email</span>
                  <input
                    type="email"
                    value={loginEmail}
                    onChange={(e) => setLoginEmail(e.target.value)}
                    required
                  />
                </label>
                <label className="form-row">
                  <span>Password</span>
                  <input
                    type="password"
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    required
                  />
                </label>
                {loginError && <p className="result-error">{loginError}</p>}
                <button type="submit" className="btn">
                  Log in
                </button>
              </form>
            )}
            {authTab === "signup" && (
              <form onSubmit={doSignup} className="form">
                <label className="form-row">
                  <span>Name</span>
                  <input
                    type="text"
                    value={signupName}
                    onChange={(e) => setSignupName(e.target.value)}
                    required
                  />
                </label>
                <label className="form-row">
                  <span>Email</span>
                  <input
                    type="email"
                    value={signupEmail}
                    onChange={(e) => setSignupEmail(e.target.value)}
                    required
                  />
                </label>
                <label className="form-row">
                  <span>Password</span>
                  <input
                    type="password"
                    value={signupPassword}
                    onChange={(e) => setSignupPassword(e.target.value)}
                    required
                  />
                </label>
                <label className="form-row">
                  <span>Payment method ID</span>
                  <input
                    type="text"
                    value={signupPaymentId}
                    onChange={(e) => setSignupPaymentId(e.target.value)}
                    required
                  />
                </label>
                {signupError && <p className="result-error">{signupError}</p>}
                <button type="submit" className="btn">
                  Sign up
                </button>
              </form>
            )}
          </div>
        </main>
        <ToastContainer toasts={toasts} remove={removeToast} />
      </>
    );
  }

  // Logged-in views
  return (
    <>
      <main className="app">
        {view === "home" && (
          <>
            <div className="card app-card">
              <h1 className="app-title">TLVFlow</h1>
              <p className="app-tagline">Hi, {user?.name}</p>
            </div>
            <div className="card section-card">
              <h2 className="section-title">Menu</h2>
              <div className="form" style={{ gap: "0.5rem" }}>
                <button
                  type="button"
                  className="btn"
                  onClick={() => setView("findStation")}
                >
                  Find nearest station
                </button>
                {!activeRide && (
                  <button
                    type="button"
                    className="btn"
                    onClick={() => setView("startRide")}
                  >
                    Start ride
                  </button>
                )}
                {activeRide && (
                  <button
                    type="button"
                    className="btn"
                    onClick={() => setView("endRide")}
                  >
                    End ride
                  </button>
                )}
                <button
                  type="button"
                  className="btn"
                  onClick={() => setView("rideHistory")}
                >
                  Ride history
                </button>
                {!user?.is_pro && (
                  <button
                    type="button"
                    className="btn"
                    onClick={() => setView("upgradePro")}
                  >
                    Upgrade to Pro
                  </button>
                )}
                {activeRide && (
                  <button
                    type="button"
                    className="btn"
                    onClick={() => setView("reportVehicle")}
                    title="Report current vehicle as degraded"
                  >
                    Report degraded vehicle
                  </button>
                )}
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setView("profile")}
                >
                  My data
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={logout}
                >
                  Logout
                </button>
              </div>
            </div>
          </>
        )}

        {view === "findStation" && (
          <div className="card section-card">
            <div className="view-header">
              <button
                type="button"
                className="view-back"
                onClick={() => setView("home")}
              >
                Back
              </button>
            </div>
            <h2 className="section-title">Find nearest station</h2>
            <button type="button" className="btn" onClick={useMyLocation}>
              Use my location
            </button>
            {nearestError && (
              <p className="result-error">{nearestError}</p>
            )}
            {nearestResult && (
              <div className="result-block">
                <p>
                  <strong>{nearestResult.name}</strong> (ID:{" "}
                  {nearestResult.station_id})
                </p>
                <p>
                  Lat: {nearestResult.lat}, Lon: {nearestResult.lon}
                </p>
                <p>
                  Capacity: {nearestResult.capacity}, Available:{" "}
                  {nearestResult.available_slots}
                </p>
              </div>
            )}
          </div>
        )}

        {view === "startRide" && (
          <div className="card section-card">
            <div className="view-header">
              <button
                type="button"
                className="view-back"
                onClick={() => setView("home")}
              >
                Back
              </button>
            </div>
            <h2 className="section-title">Start ride</h2>
            <p className="section-note">
              Be within 5 m of a station to start. We'll use your location to
              find the nearest station.
            </p>
            <button
              type="button"
              className="btn"
              onClick={useMyLocationForStart}
              disabled={startLocationLoading}
            >
              {startLocationLoading ? "Getting location…" : "Use my location"}
            </button>
            {startError && (
              <p className="result-error">{startError}</p>
            )}
            {startNearestStation && (
              <div className="result-block">
                {startUserPosition && (
                  <p className="section-note">
                    Your position: {startUserPosition.lat.toFixed(5)},{" "}
                    {startUserPosition.lon.toFixed(5)}
                  </p>
                )}
                <p>
                  <strong>Nearest station:</strong> {startNearestStation.name}{" "}
                  (ID: {startNearestStation.station_id}) —{" "}
                  {startNearestStation.distance_m} m away
                </p>
                {startAtStation ? (
                  <form
                    onSubmit={(e) =>
                      doStartRideFromStation(e)
                    }
                  >
                    <button
                      type="submit"
                      className="btn"
                      disabled={startSubmitLoading}
                    >
                      {startSubmitLoading
                        ? "Starting…"
                        : `Start ride from ${startNearestStation.name}`}
                    </button>
                  </form>
                ) : (
                  <p className="result-error">
                    You must be within 5 m of a station. Enter your location
                    manually below or move closer.
                  </p>
                )}
              </div>
            )}
            <h3 className="section-title" style={{ marginTop: "1rem" }}>
              Or enter location manually
            </h3>
            <form
              onSubmit={checkManualLocationForStart}
              className="form"
              style={{ gap: "0.5rem" }}
            >
              <label className="form-row">
                <span>Latitude</span>
                <input
                  type="text"
                  inputMode="decimal"
                  placeholder="e.g. 32.0853"
                  value={startManualLat}
                  onChange={(e) => setStartManualLat(e.target.value)}
                />
              </label>
              <label className="form-row">
                <span>Longitude</span>
                <input
                  type="text"
                  inputMode="decimal"
                  placeholder="e.g. 34.7818"
                  value={startManualLon}
                  onChange={(e) => setStartManualLon(e.target.value)}
                />
              </label>
              <button
                type="submit"
                className="btn"
                disabled={startLocationLoading}
              >
                Check distance to nearest station
              </button>
            </form>
          </div>
        )}

        {view === "endRide" && activeRide && (
          <div className="card section-card">
            <div className="view-header">
              <button
                type="button"
                className="view-back"
                onClick={() => setView("home")}
              >
                Back
              </button>
            </div>
            <h2 className="section-title">End ride</h2>
            <p className="section-note">
              Be within 5 m of a station to end the ride. Use your location or enter coordinates.
            </p>
            {endLocationLoading && (
              <p className="section-note">Getting location…</p>
            )}
            {endNearestStation && (
              <div className="result-block">
                <p>
                  <strong>Nearest station:</strong> {endNearestStation.name} (ID:{" "}
                  {endNearestStation.station_id}) — {endNearestStation.distance_m} m
                  away
                </p>
                {!endAtStation && (
                  <p className="result-error">
                    You must be within 5 m of a station to end the ride. Go to{" "}
                    {endNearestStation.name} ({endNearestStation.distance_m} m
                    away) or another station.
                  </p>
                )}
              </div>
            )}
            <form onSubmit={doEndRide} className="form">
              {endError && <p className="result-error">{endError}</p>}
              <div className="form-row">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={loadEndRideNearest}
                  disabled={endLoading || endLocationLoading}
                >
                  Use my location
                </button>
              </div>
              <p className="section-note" style={{ marginTop: "0.5rem" }}>Or enter latitude and longitude:</p>
              <div className="form-row" style={{ flexWrap: "wrap", gap: "0.5rem", alignItems: "center" }}>
                <label style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
                  <span>Lat</span>
                  <input
                    type="text"
                    inputMode="decimal"
                    placeholder="e.g. 32.0853"
                    value={endManualLat}
                    onChange={(e) => setEndManualLat(e.target.value)}
                    disabled={endLoading || endLocationLoading}
                    style={{ width: "8rem" }}
                  />
                </label>
                <label style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
                  <span>Lon</span>
                  <input
                    type="text"
                    inputMode="decimal"
                    placeholder="e.g. 34.7818"
                    value={endManualLon}
                    onChange={(e) => setEndManualLon(e.target.value)}
                    disabled={endLoading || endLocationLoading}
                    style={{ width: "8rem" }}
                  />
                </label>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={useManualEndCoordinates}
                  disabled={endLoading || endLocationLoading}
                >
                  Use these coordinates
                </button>
              </div>
              <div className="form-row">
                <button
                  type="submit"
                  className="btn"
                  disabled={
                    endLoading ||
                    !endAtStation ||
                    endLocationLoading ||
                    !endNearestStation ||
                    !endUserPosition
                  }
                >
                  {endLoading ? "Ending…" : "End ride"}
                </button>
              </div>
            </form>
          </div>
        )}

        {view === "profile" && (
          <div className="card section-card">
            <div className="view-header">
              <button
                type="button"
                className="view-back"
                onClick={() => setView("home")}
              >
                Back
              </button>
            </div>
            <h2 className="section-title">My data</h2>
            {profileError && (
              <p className="result-error">{profileError}</p>
            )}
            {profile && (
              <>
                <p>Name: {profile.name}</p>
                <p>Email: {profile.email}</p>
                <p>Payment method ID: {profile.payment_method_id || "—"}</p>
                <p>{profile.is_pro ? "Pro user" : "Standard user"}</p>
                <form onSubmit={updatePaymentMethod} className="form">
                  <label className="form-row">
                    <span>Update payment method ID</span>
                    <input
                      type="text"
                      value={newPaymentId}
                      onChange={(e) => setNewPaymentId(e.target.value)}
                    />
                  </label>
                  {profilePaymentError && (
                    <p className="result-error">{profilePaymentError}</p>
                  )}
                  <button type="submit" className="btn">
                    Update
                  </button>
                </form>
              </>
            )}
          </div>
        )}

        {view === "rideHistory" && (
          <div className="card section-card">
            <div className="view-header">
              <button
                type="button"
                className="view-back"
                onClick={() => setView("home")}
              >
                Back
              </button>
            </div>
            <h2 className="section-title">Ride history</h2>
            {rideHistoryError && (
              <p className="result-error">{rideHistoryError}</p>
            )}
            {rideHistory.length === 0 && !rideHistoryError && (
              <p className="section-note">No past rides.</p>
            )}
            {rideHistory.length > 0 && (
              <ul className="result-block" style={{ listStyle: "none", paddingLeft: 0 }}>
                {rideHistory.map((r) => (
                  <li key={r.ride_id} className="ride-history-item" style={{ marginBottom: "1rem", padding: "0.75rem", border: "1px solid var(--border)", borderRadius: "6px", display: "flex", flexWrap: "wrap", alignItems: "center", gap: "0.5rem 1rem" }}>
                    <span><strong>Vehicle {r.vehicle_id}</strong></span>
                    <span className="ride-history-times" style={{ color: "var(--text-muted)" }}>
                      {formatRideDateTime(r.start_time)} → {formatRideDateTime(r.end_time)}
                    </span>
                    {typeof r.fee === "number" && (
                      <span style={{ color: "var(--text-muted)" }}>{r.fee} ILS</span>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {view === "upgradePro" && (
          <div className="card section-card">
            <div className="view-header">
              <button
                type="button"
                className="view-back"
                onClick={() => setView("home")}
              >
                Back
              </button>
            </div>
            <h2 className="section-title">Upgrade to Pro</h2>
            <p className="section-note">
              Add your driver's license to upgrade (one-time).
            </p>
            <form onSubmit={doUpgrade} className="form">
              <label className="form-row">
                <span>License number</span>
                <input
                  type="text"
                  value={licenseNumber}
                  onChange={(e) => setLicenseNumber(e.target.value)}
                  required
                />
              </label>
              <label className="form-row">
                <span>License expiry (ISO date)</span>
                <input
                  type="text"
                  value={licenseExpiry}
                  onChange={(e) => setLicenseExpiry(e.target.value)}
                  placeholder="e.g. 2028-12-31"
                  required
                />
              </label>
              <label className="form-row">
                <span>License image URL (optional)</span>
                <input
                  type="url"
                  value={licenseImageUrl}
                  onChange={(e) => setLicenseImageUrl(e.target.value)}
                  placeholder="https://..."
                />
              </label>
              {upgradeError && (
                <p className="result-error">{upgradeError}</p>
              )}
              <button type="submit" className="btn" disabled={upgradeLoading}>
                {upgradeLoading ? "Upgrading…" : "Upgrade to Pro"}
              </button>
            </form>
          </div>
        )}

        {view === "reportVehicle" && (
          <div className="card section-card">
            <div className="view-header">
              <button
                type="button"
                className="view-back"
                onClick={() => setView("home")}
              >
                Back
              </button>
            </div>
            <h2 className="section-title">Report degraded vehicle</h2>
            {activeRide ? (
              <>
                <p className="section-note">
                  You are riding <strong>Vehicle {activeRide.vehicle_id}</strong>. Reporting it as degraded will end your ride at no charge.
                </p>
                <form onSubmit={doReport} className="form">
                  {reportError && <p className="result-error">{reportError}</p>}
                  <button type="submit" className="btn" disabled={reportLoading}>
                    {reportLoading ? "Reporting…" : "Report degraded vehicle"}
                  </button>
                </form>
              </>
            ) : (
              <p className="section-note">
                You can report a vehicle as degraded only during an active ride. It will end the ride at no charge. Start a ride to see the option.
              </p>
            )}
          </div>
        )}
      </main>
      <ToastContainer toasts={toasts} remove={removeToast} />
    </>
  );
}

export default App;
