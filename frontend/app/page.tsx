'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';

type Scope = 'Day' | 'Week' | 'Month';
type Display = 'Calendar' | 'List';
type Member = { id:string; name:string; role:'Child'|'Parent'; color:string; details:string };
type Guest = { id:string; name:string; contact:string };
type GuestReminder = { id:string; guestId:string; timing:string; channel:'Text'|'Email' };
type Activity = { id:string; title:string; date:string; time:string; endTime:string; person:string; parent:string; location:string; color:string; guests?:Guest[]; guestReminders?:GuestReminder[]; source?:'family'|'school'; note?:string };

const TODAY = '2026-08-30';
const STORAGE_KEY = 'kinday-family-1-calendar-v2';
const colors = ['#cf765d','#6595a7','#d1aa3f','#75906b','#9a7fac'];
const initialMembers:Member[] = [
  {id:'m1',name:'Maya',role:'Child',color:colors[0],details:'Age 10 · Grade 5'},
  {id:'m2',name:'Leo',role:'Child',color:colors[1],details:'Age 7 · Grade 2'},
  {id:'m3',name:'Anusha',role:'Parent',color:colors[3],details:'Primary contact'},
  {id:'m4',name:'Vikram',role:'Parent',color:colors[4],details:'Pickup contact · Unavailable Tue–Thu, 9:30 AM–4 PM'},
];
const initialActivities:Activity[] = [
  {id:'db-01',title:'Family planning breakfast',date:'2026-08-30',time:'09:00',endTime:'10:00',person:'Everyone',parent:'Anusha',location:'Home',color:colors[2]},
  {id:'db-02',title:'Child-2 piano lesson',date:'2026-09-01',time:'16:00',endTime:'17:00',person:'Maya',parent:'Everyone',location:'Music School',color:colors[0],note:'Pickup and drop-off required · Bring music folder.'},
  {id:'db-03',title:'Leo soccer practice',date:'2026-09-01',time:'16:00',endTime:'17:30',person:'Leo',parent:'Everyone',location:'Community Field',color:colors[1],note:'Pickup and drop-off required · Bring cleats and water.'},
  {id:'db-04',title:'Leo swim practice',date:'2026-09-03',time:'17:00',endTime:'18:00',person:'Leo',parent:'Vikram',location:'Aquatic Center',color:colors[1],note:'Pickup and drop-off required.'},
  {id:'db-05',title:'Family hike',date:'2026-09-06',time:'09:30',endTime:'12:30',person:'Everyone',parent:'Everyone',location:'Alum Rock Park',color:colors[3]},
  {id:'db-06',title:'Child-2 piano lesson',date:'2026-09-08',time:'16:00',endTime:'17:00',person:'Maya',parent:'Everyone',location:'Music School',color:colors[0],note:'Pickup and drop-off required · Bring music folder.'},
  {id:'db-07',title:'Leo soccer practice',date:'2026-09-08',time:'16:00',endTime:'17:30',person:'Leo',parent:'Everyone',location:'Community Field',color:colors[1],note:'Pickup and drop-off required · Bring cleats and water.'},
  {id:'db-08',title:'Child-2 dentist appointment',date:'2026-09-09',time:'13:00',endTime:'14:00',person:'Maya',parent:'Anusha',location:'San Jose Pediatric Dental',color:colors[0],note:'During school hours · Pickup and drop-off required.'},
  {id:'db-09',title:'Leo swim practice',date:'2026-09-10',time:'17:00',endTime:'18:00',person:'Leo',parent:'Vikram',location:'Aquatic Center',color:colors[1],note:'Pickup and drop-off required.'},
  {id:'db-10',title:'Kids science workshop',date:'2026-09-12',time:'10:00',endTime:'12:00',person:'Leo',parent:'Vikram',location:'The Tech Interactive',color:colors[1],note:'Pickup and drop-off required.'},
  {id:'db-11',title:'Child-2 piano lesson',date:'2026-09-15',time:'16:00',endTime:'17:00',person:'Maya',parent:'Everyone',location:'Music School',color:colors[0],note:'Pickup and drop-off required · Bring music folder.'},
  {id:'db-12',title:'Leo soccer practice',date:'2026-09-15',time:'16:00',endTime:'17:30',person:'Leo',parent:'Everyone',location:'Community Field',color:colors[1],note:'Pickup and drop-off required · Bring cleats and water.'},
  {id:'db-13',title:'Parent-teacher conference',date:'2026-09-17',time:'14:30',endTime:'15:15',person:'Leo',parent:'Anusha',location:'Maple Grove Elementary',color:colors[1],note:'Overlaps normal school hours.'},
  {id:'db-14',title:'Leo swim practice',date:'2026-09-17',time:'17:00',endTime:'18:00',person:'Leo',parent:'Vikram',location:'Aquatic Center',color:colors[1],note:'Pickup and drop-off required.'},
  {id:'db-15',title:"Maya's birthday party",date:'2026-09-20',time:'14:00',endTime:'16:30',person:'Maya',parent:'Anusha',location:'Community Center',color:colors[0],note:'Pickup and drop-off required.'},
  {id:'db-16',title:'Child-2 piano lesson',date:'2026-09-22',time:'16:00',endTime:'17:00',person:'Maya',parent:'Everyone',location:'Music School',color:colors[0],note:'Pickup and drop-off required · Bring music folder.'},
  {id:'db-17',title:'Leo soccer practice',date:'2026-09-22',time:'16:00',endTime:'17:30',person:'Leo',parent:'Everyone',location:'Community Field',color:colors[1],note:'Pickup and drop-off required · Bring cleats and water.'},
  {id:'db-18',title:'Leo swim practice',date:'2026-09-24',time:'17:00',endTime:'18:00',person:'Leo',parent:'Vikram',location:'Aquatic Center',color:colors[1],note:'Pickup and drop-off required.'},
  {id:'db-19',title:'Family picnic',date:'2026-09-26',time:'11:30',endTime:'14:00',person:'Everyone',parent:'Everyone',location:'Vasona Lake County Park',color:colors[3]},
  {id:'db-20',title:'Child-2 piano lesson',date:'2026-09-29',time:'16:00',endTime:'17:00',person:'Maya',parent:'Everyone',location:'Music School',color:colors[0],note:'Pickup and drop-off required · Bring music folder.'},
  {id:'db-21',title:'Leo soccer practice',date:'2026-09-29',time:'16:00',endTime:'17:30',person:'Leo',parent:'Everyone',location:'Community Field',color:colors[1],note:'Pickup and drop-off required · Bring cleats and water.'},
];
const schoolActivities:Activity[] = [
  {id:'s1',title:'Spirit Day: Blue & Gold',date:'2026-08-28',time:'09:00',endTime:'15:00',person:'School',parent:'Maple Grove Elementary',location:'Maple Grove Elementary',color:'#8a769d',source:'school',note:'Wear blue & gold or a school-spirit shirt.'},
  {id:'s2',title:'Back to School Night',date:'2026-09-01',time:'16:30',endTime:'18:00',person:'School',parent:'Maple Grove Elementary',location:'Maple Grove Elementary',color:'#8a769d',source:'school',note:'Timed school event; check family transportation and supervision.'},
  {id:'s3',title:'Picture Day',date:'2026-09-02',time:'09:00',endTime:'15:00',person:'School',parent:'Maple Grove Elementary',location:'Maple Grove Elementary',color:'#8a769d',source:'school',note:'No exact time was published.'},
  {id:'s4',title:'Activity Day: Blacktop Games',date:'2026-09-04',time:'09:00',endTime:'15:00',person:'School',parent:'Maple Grove Elementary',location:'Maple Grove Elementary',color:'#8a769d',source:'school',note:'No exact time was published.'},
  {id:'s5',title:'No School: Labor Day',date:'2026-09-07',time:'09:00',endTime:'15:00',person:'School',parent:'Maple Grove Elementary',location:'School closed',color:'#b46755',source:'school',note:'School is closed; normal school-hour assumptions do not apply.'},
  {id:'s6',title:'Bingo Night',date:'2026-09-18',time:'18:00',endTime:'19:30',person:'School',parent:'Maple Grove Elementary',location:'Maple Grove Elementary',color:'#8a769d',source:'school',note:'Timed school event.'},
];
const formatTime=(time:string)=>new Date(`2026-01-01T${time}`).toLocaleTimeString('en-US',{hour:'numeric',minute:'2-digit'});
const prettyDate=(date:string)=>new Date(`${date}T12:00:00`).toLocaleDateString('en-US',{weekday:'long',month:'long',day:'numeric'});
const toISO=(date:Date)=>`${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
const fromISO=(date:string)=>new Date(`${date}T12:00:00`);
const addDays=(date:Date,days:number)=>{const next=new Date(date);next.setDate(next.getDate()+days);return next};
const weekFor=(date:string)=>{const focus=fromISO(date);const monday=addDays(focus,-((focus.getDay()+6)%7));return Array.from({length:7},(_,i)=>{const value=addDays(monday,i);return{date:toISO(value),label:value.toLocaleDateString('en-US',{weekday:'short'}).toUpperCase(),day:value.getDate()}})};

export default function Home(){
  const [scope,setScope]=useState<Scope>('Month');
  const [display,setDisplay]=useState<Display>('Calendar');
  const [activities,setActivities]=useState<Activity[]>(initialActivities);
  const [members,setMembers]=useState<Member[]>(initialMembers);
  const [filter,setFilter]=useState('Everyone');
  const [panel,setPanel]=useState<'event'|'family'|'planner'|null>(null);
  const [selectedEventId,setSelectedEventId]=useState<string|null>(null);
  const [showSchool,setShowSchool]=useState(true);
  const [toast,setToast]=useState('');
  const [selectedDate,setSelectedDate]=useState(TODAY);

  useEffect(()=>{const saved=localStorage.getItem(STORAGE_KEY);if(saved){try{const data=JSON.parse(saved);setActivities(data.activities||initialActivities);setMembers(data.members||initialMembers)}catch{}}},[]);
  useEffect(()=>{localStorage.setItem(STORAGE_KEY,JSON.stringify({activities,members}))},[activities,members]);

  const visible=useMemo(()=>[...activities,...(showSchool?schoolActivities:[])].filter(a=>filter==='Everyone'||a.person===filter||a.source==='school').sort((a,b)=>(a.date+a.time).localeCompare(b.date+b.time)),[activities,filter,showSchool]);
  const weekDays=useMemo(()=>weekFor(selectedDate),[selectedDate]);
  const selected=fromISO(selectedDate);
  const monthKey=selectedDate.slice(0,7);
  const scoped=useMemo(()=>visible.filter(a=>(scope==='Month'&&a.date.startsWith(monthKey))||(scope==='Week'&&weekDays.some(d=>d.date===a.date))||(scope==='Day'&&a.date===selectedDate)),[visible,scope,selectedDate,monthKey,weekDays]);
  const title=scope==='Day'?prettyDate(selectedDate):scope==='Week'?`${new Date(`${weekDays[0].date}T12:00:00`).toLocaleDateString('en-US',{month:'short',day:'numeric'})}–${new Date(`${weekDays[6].date}T12:00:00`).toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'})}`:selected.toLocaleDateString('en-US',{month:'long',year:'numeric'});
  const announce=(message:string)=>{setToast(message);window.setTimeout(()=>setToast(''),3500)};
  const navigate=(direction:-1|1)=>{const current=fromISO(selectedDate);if(scope==='Month')current.setMonth(current.getMonth()+direction);else current.setDate(current.getDate()+direction*(scope==='Week'?7:1));setSelectedDate(toISO(current))};
  const selectedEvent=[...activities,...schoolActivities].find(activity=>activity.id===selectedEventId)||null;
  const updateEvent=(id:string,change:(item:Activity)=>Activity)=>setActivities(items=>items.map(item=>item.id===id?change(item):item));

  function addEvent(e:FormEvent<HTMLFormElement>){
    e.preventDefault(); const data=new FormData(e.currentTarget); const person=String(data.get('person')); const member=members.find(m=>m.name===person);
    const item:Activity={id:crypto.randomUUID(),title:String(data.get('title')),date:String(data.get('date')),time:String(data.get('time')),endTime:String(data.get('endTime')),person,parent:String(data.get('parent')),location:String(data.get('location')),color:member?.color||colors[2]};
    setActivities(items=>[...items,item]);setSelectedDate(item.date);setPanel(null);announce(`${item.title} added to the calendar`);
  }
  function addMember(e:FormEvent<HTMLFormElement>){
    e.preventDefault();const data=new FormData(e.currentTarget);const role=String(data.get('role')) as Member['role'];const name=String(data.get('name'));
    setMembers(items=>[...items,{id:crypto.randomUUID(),name,role,color:colors[items.length%colors.length],details:String(data.get('details'))}]);e.currentTarget.reset();announce(`${name} added to your family`);
  }
  function addGuest(e:FormEvent<HTMLFormElement>){
    e.preventDefault();if(!selectedEvent)return;const data=new FormData(e.currentTarget);const guest:Guest={id:crypto.randomUUID(),name:String(data.get('guestName')),contact:String(data.get('contact'))};updateEvent(selectedEvent.id,item=>({...item,guests:[...(item.guests||[]),guest]}));e.currentTarget.reset();announce(`${guest.name} added as a guest`);
  }
  function addGuestReminder(e:FormEvent<HTMLFormElement>){
    e.preventDefault();if(!selectedEvent)return;const data=new FormData(e.currentTarget);const reminder:GuestReminder={id:crypto.randomUUID(),guestId:String(data.get('guestId')),timing:String(data.get('timing')),channel:String(data.get('channel')) as GuestReminder['channel']};updateEvent(selectedEvent.id,item=>({...item,guestReminders:[...(item.guestReminders||[]),reminder]}));announce('Guest reminder saved as a draft');
  }

  return <main className="shell">
    <header className="topbar">
      <a className="brand" href="#"><span className="sprout"><i/><i/><i/></span>Kin<b>day</b></a>
      <nav><a className="active" href="#calendar">Calendar</a><button onClick={()=>setPanel('family')}>Family</button><a href="#reminders">Reminders</a></nav>
      <div className="top-actions"><button className="family-button" onClick={()=>setPanel('family')}>◉ Family setup</button><span className="avatar">AK</span></div>
    </header>

    <section className="calendar-shell" id="calendar">
      <header className="calendar-header">
        <div><p className="eyebrow">FAMILY-1 · SQLITE SNAPSHOT</p><h1>{title}</h1><p className="sync-note">21 seeded activities · Aug 30–Sep 29, 2026</p></div>
        <div className="header-actions"><button className="secondary" onClick={()=>setPanel('planner')}>✦ Review week</button><button className="secondary" onClick={()=>setSelectedDate(TODAY)}>Today</button><div className="arrows"><button aria-label={`Previous ${scope.toLowerCase()}`} onClick={()=>navigate(-1)}>‹</button><button aria-label={`Next ${scope.toLowerCase()}`} onClick={()=>navigate(1)}>›</button></div><button className="primary" onClick={()=>setPanel('event')}>＋ Add activity</button></div>
      </header>

      <div className="controls">
        <div className="segmented" aria-label="Calendar range">{(['Day','Week','Month'] as Scope[]).map(x=><button className={scope===x?'selected':''} onClick={()=>setScope(x)} key={x}>{x}</button>)}</div>
        <div className="member-filter"><button className={filter==='Everyone'?'selected':''} onClick={()=>setFilter('Everyone')}>Everyone</button>{members.filter(m=>m.role==='Child').map(m=><button className={filter===m.name?'selected':''} onClick={()=>setFilter(m.name)} key={m.id}><i style={{background:m.color}}>{m.name[0]}</i>{m.name}</button>)}<button className={showSchool?'selected school-filter':''} onClick={()=>setShowSchool(value=>!value)}><i>R</i>School {showSchool?'on':'off'}</button></div>
        <div className="view-toggle" aria-label="Display style"><button className={display==='Calendar'?'selected':''} onClick={()=>setDisplay('Calendar')} aria-label="Calendar view">▦</button><button className={display==='List'?'selected':''} onClick={()=>setDisplay('List')} aria-label="List view">☷</button></div>
      </div>

      {display==='List'?<ListView activities={scoped} onOpen={setSelectedEventId}/>:scope==='Month'?<MonthView activities={visible} focusDate={selectedDate} onDay={date=>{setSelectedDate(date);setScope('Day')}} onOpen={setSelectedEventId}/>:scope==='Day'?<DayView date={selectedDate} activities={scoped} onOpen={setSelectedEventId}/>:<WeekView activities={visible} days={weekDays} onOpen={setSelectedEventId}/>}
    </section>

    <section className="lower-grid" id="reminders">
      <article className="summary-card"><span className="card-kicker">TODAY AT A GLANCE</span><strong>{visible.filter(a=>a.date===TODAY).length}</strong><p>activities · {activities.length} family events loaded</p></article>
      <article className="reminders"><header><span className="card-kicker">UPCOMING TRANSPORTATION</span><button onClick={()=>{setSelectedDate('2026-09-01');setScope('Day')}}>View day</button></header><div><i>◌</i><p><strong>Piano folder + pickup</strong><span>Sep 1 at 4:00 PM · Parent unassigned</span></p><em>Needs plan</em></div><div><i>◌</i><p><strong>Soccer cleats + water</strong><span>Sep 1 at 4:00 PM · Parent unassigned</span></p><em>Needs plan</em></div></article>
    </section>

    {panel&&<div className="overlay" onMouseDown={e=>{if(e.target===e.currentTarget)setPanel(null)}}><aside className="drawer" aria-label={panel==='event'?'Add activity':panel==='planner'?'Weekly review':'Family details'}><header><div><p className="eyebrow">{panel==='event'?'NEW ACTIVITY':panel==='planner'?'COORDINATED PLAN':'YOUR HOUSEHOLD'}</p><h2>{panel==='event'?'Add to the calendar':panel==='planner'?'Weekly review':'Family details'}</h2></div><button className="close" onClick={()=>setPanel(null)}>×</button></header>{panel==='event'?<EventForm members={members} onSubmit={addEvent}/>:panel==='planner'?<WeeklyReview days={weekDays} activities={visible}/>:<FamilyPanel members={members} onSubmit={addMember} onRemove={id=>setMembers(items=>items.filter(m=>m.id!==id))}/>}</aside></div>}
    {selectedEvent&&<div className="overlay centered" onMouseDown={e=>{if(e.target===e.currentTarget)setSelectedEventId(null)}}><EventDetails item={selectedEvent} onClose={()=>setSelectedEventId(null)} onAddGuest={addGuest} onAddReminder={addGuestReminder} onRemoveGuest={guestId=>updateEvent(selectedEvent.id,item=>({...item,guests:(item.guests||[]).filter(g=>g.id!==guestId),guestReminders:(item.guestReminders||[]).filter(r=>r.guestId!==guestId)}))}/></div>}
    {toast&&<div className="toast" role="status">✓ {toast}</div>}
  </main>;
}

function EventForm({members,onSubmit}:{members:Member[];onSubmit:(e:FormEvent<HTMLFormElement>)=>void}){
  return <form className="form" onSubmit={onSubmit}><label>Activity name<input name="title" required placeholder="e.g. Soccer practice" autoFocus/></label><div className="form-row"><label>Date<input name="date" type="date" defaultValue={TODAY} required/></label><label>Starts<input name="time" type="time" defaultValue="16:00" required/></label></div><div className="form-row"><label>Ends<input name="endTime" type="time" defaultValue="17:00" required/></label><label>Child<select name="person" required><option>Everyone</option>{members.filter(m=>m.role==='Child').map(m=><option key={m.id}>{m.name}</option>)}</select></label></div><label>Responsible parent<select name="parent"><option>Everyone</option>{members.filter(m=>m.role==='Parent').map(m=><option key={m.id}>{m.name}</option>)}</select></label><label>Location<input name="location" placeholder="Optional location"/></label><div className="policy-note"><span>!</span><p>Kinday checks school hours, Maple Grove calendar dates, family overlaps, and Vikram’s Tue–Thu transportation availability during weekly review.</p></div><div className="approval-note"><span>✓</span><p><strong>You stay in control</strong>New activities appear immediately here. Connected-calendar changes will still require your approval.</p></div><button className="submit" type="submit">Add activity</button></form>;
}
function FamilyPanel({members,onSubmit,onRemove}:{members:Member[];onSubmit:(e:FormEvent<HTMLFormElement>)=>void;onRemove:(id:string)=>void}){
  return <div className="family-panel"><div className="member-list">{members.map(m=><article key={m.id}><i style={{background:m.color}}>{m.name[0]}</i><div><strong>{m.name}</strong><span>{m.role} · {m.details}</span></div><button onClick={()=>onRemove(m.id)} aria-label={`Remove ${m.name}`}>×</button></article>)}</div><h3>Add a family member</h3><form className="form compact" onSubmit={onSubmit}><label>Name<input name="name" required placeholder="Full name"/></label><div className="form-row"><label>Role<select name="role"><option>Child</option><option>Parent</option></select></label><label>Details<input name="details" placeholder="Age, grade, contact…"/></label></div><button className="submit">Add person</button></form></div>;
}
function WeekView({activities,days,onOpen}:{activities:Activity[];days:{date:string;label:string;day:number}[];onOpen:(id:string)=>void}){return <div className="week-grid">{days.map(d=><article className={`day-column ${d.date===TODAY?'today-col':''}`} key={d.date}><header><span>{d.label}</span><strong>{d.day}</strong></header><div className="day-events">{activities.filter(a=>a.date===d.date).map(a=><EventCard item={a} onOpen={onOpen} key={a.id}/>)}</div></article>)}</div>}
function DayView({date,activities,onOpen}:{date:string;activities:Activity[];onOpen:(id:string)=>void}){return <div className="day-view"><div className="time-rail">{['8 AM','10 AM','12 PM','2 PM','4 PM','6 PM','8 PM'].map(x=><span key={x}>{x}</span>)}</div><div className="day-track">{activities.length?activities.map((a,i)=><div className="day-event" key={a.id} style={{borderColor:a.color,top:`${40+i*92}px`}}><EventCard item={a} onOpen={onOpen}/></div>):<Empty/>}</div></div>}
function MonthView({activities,focusDate,onDay,onOpen}:{activities:Activity[];focusDate:string;onDay:(date:string)=>void;onOpen:(id:string)=>void}){const focus=fromISO(focusDate);const year=focus.getFullYear();const month=focus.getMonth();const first=new Date(year,month,1,12);const blanks=(first.getDay()+6)%7;const count=new Date(year,month+1,0).getDate();const previousCount=new Date(year,month,0).getDate();return <div className="month"><header>{['MON','TUE','WED','THU','FRI','SAT','SUN'].map(x=><span key={x}>{x}</span>)}</header><div className="month-grid">{Array.from({length:blanks},(_,i)=><div className="month-day muted" key={`b${i}`}>{previousCount-blanks+i+1}</div>)}{Array.from({length:count},(_,i)=>{const day=i+1;const date=toISO(new Date(year,month,day,12));const items=activities.filter(a=>a.date===date);return <div className={`month-day ${date===TODAY?'today-cell':''}`} key={day}><button className="month-number" onClick={()=>onDay(date)}><strong>{day}</strong></button>{items.slice(0,3).map(a=><button className="month-event" onClick={()=>onOpen(a.id)} key={a.id} style={{borderColor:a.color}}>{a.time} {a.title}</button>)}{items.length>3&&<small>+{items.length-3} more</small>}</div>})}</div></div>}
function ListView({activities,onOpen}:{activities:Activity[];onOpen:(id:string)=>void}){if(!activities.length)return <Empty/>;let last='';return <div className="list-view">{activities.map(a=>{const show=a.date!==last;last=a.date;return <div key={a.id}>{show&&<h3>{prettyDate(a.date)}</h3>}<article onClick={()=>onOpen(a.id)} role="button" tabIndex={0}><i style={{background:a.color}}/><time>{formatTime(a.time)}</time><div><strong>{a.title}</strong><span>{a.person} · {a.parent} · {a.location||'No location'}</span></div><button aria-label={`Open ${a.title}`}>•••</button></article></div>})}</div>}
function EventCard({item,onOpen}:{item:Activity;onOpen:(id:string)=>void}){return <button className="event-card" onClick={()=>onOpen(item.id)} style={{background:`color-mix(in srgb, ${item.color} 17%, white)`,borderColor:item.color}}><small>{formatTime(item.time)}</small><strong>{item.title}</strong><span>{item.location||'No location'}</span><footer><i style={{background:item.color}}>{item.person[0]}</i>{item.person}{item.guests?.length?<b>+{item.guests.length} guest{item.guests.length>1?'s':''}</b>:null}</footer></button>}
function EventDetails({item,onClose,onAddGuest,onAddReminder,onRemoveGuest}:{item:Activity;onClose:()=>void;onAddGuest:(e:FormEvent<HTMLFormElement>)=>void;onAddReminder:(e:FormEvent<HTMLFormElement>)=>void;onRemoveGuest:(id:string)=>void}){
  const guests=item.guests||[];const reminders=item.guestReminders||[];
  return <section className="event-modal" role="dialog" aria-modal="true" aria-labelledby="event-title">
    <header style={{borderColor:item.color}}><div><p className="eyebrow">EVENT DETAILS</p><h2 id="event-title">{item.title}</h2></div><button className="close" onClick={onClose}>×</button></header>
    <div className="event-facts"><div><span>DATE</span><strong>{prettyDate(item.date)}</strong></div><div><span>TIME</span><strong>{formatTime(item.time)}–{formatTime(item.endTime)}</strong></div><div><span>FOR</span><strong>{item.person}</strong></div><div><span>{item.source==='school'?'SOURCE':'RESPONSIBLE'}</span><strong>{item.parent}</strong></div><div className="wide"><span>LOCATION</span><strong>⌖ {item.location||'No location added'}</strong></div>{item.note&&<div className="wide source-note"><span>PLANNING NOTE</span><strong>{item.note}</strong></div>}</div>
    {item.source==='school'?<div className="school-source"><strong>Supplied Maple Grove Elementary 2026–2027 calendar</strong><p>This is reviewed reference data, not a live school feed. Dates are subject to change.</p></div>:<><div className="guest-section"><div className="modal-heading"><div><p className="eyebrow">GUESTS</p><h3>Family & friends</h3></div><span>{guests.length}</span></div>
      {guests.length?<div className="guest-list">{guests.map(guest=><article key={guest.id}><i>{guest.name[0]}</i><div><strong>{guest.name}</strong><span>{guest.contact}</span></div><small>{reminders.filter(r=>r.guestId===guest.id).length} reminder{reminders.filter(r=>r.guestId===guest.id).length===1?'':'s'}</small><button onClick={()=>onRemoveGuest(guest.id)} aria-label={`Remove ${guest.name}`}>×</button></article>)}</div>:<p className="guest-empty">Invite grandparents, relatives, or friends who should know about this event.</p>}
      <form className="guest-form" onSubmit={onAddGuest}><input name="guestName" required placeholder="Guest name" aria-label="Guest name"/><input name="contact" required placeholder="Email or mobile number" aria-label="Guest contact"/><button>Add guest</button></form>
    </div>
    <div className="guest-section reminder-builder"><div className="modal-heading"><div><p className="eyebrow">REMINDERS</p><h3>Remind a guest</h3></div></div>
      {guests.length?<form onSubmit={onAddReminder}><select name="guestId" aria-label="Guest">{guests.map(g=><option value={g.id} key={g.id}>{g.name}</option>)}</select><select name="timing" aria-label="Reminder timing"><option>1 day before</option><option>2 hours before</option><option>1 hour before</option><option>30 minutes before</option></select><select name="channel" aria-label="Reminder channel"><option>Text</option><option>Email</option></select><button>Save reminder</button></form>:<p className="guest-empty">Add a guest first, then choose when and how to remind them.</p>}
      {reminders.length>0&&<div className="saved-reminders">{reminders.map(reminder=>{const guest=guests.find(g=>g.id===reminder.guestId);return <div key={reminder.id}><span>◌</span><p><strong>{guest?.name||'Guest'} · {reminder.channel}</strong><small>{reminder.timing} · Saved draft</small></p></div>})}</div>}
      <p className="delivery-note">Reminders are saved as drafts in this version; no text or email is sent yet.</p>
    </div></>}
  </section>
}
function WeeklyReview({days,activities}:{days:{date:string;label:string;day:number}[];activities:Activity[]}){
  const inWeek=activities.filter(a=>days.some(day=>day.date===a.date));
  const findings=inWeek.flatMap(item=>{
    const date=fromISO(item.date);const weekday=date.getDay();const notes:string[]=[];
    if(item.source==='school')notes.push(`${item.title}: Maple Grove calendar planning note`);
    if(item.source!=='school'&&weekday>0&&weekday<6&&item.time<'15:00')notes.push(`${item.title}: overlaps regular school hours`);
    if(item.parent.toLowerCase()==='vikram'&&weekday>=2&&weekday<=4&&item.time<'16:00'&&item.endTime>'09:30')notes.push(`${item.title}: Vikram is unavailable for transportation`);
    return notes;
  });
  return <div className="weekly-review"><div className="review-status"><span>✓</span><div><strong>Schedule reviewer complete</strong><p>{findings.length?`${findings.length} item${findings.length===1?'':'s'} need attention before approval.`:'No blocking findings in the visible week.'}</p></div></div><section><p className="eyebrow">WEEK AT A GLANCE</p><div className="review-stats"><div><strong>{inWeek.filter(a=>a.source!=='school').length}</strong><span>family events</span></div><div><strong>{inWeek.filter(a=>a.source==='school').length}</strong><span>school notes</span></div><div><strong>{findings.length}</strong><span>findings</span></div></div></section><section><p className="eyebrow">REVIEW FINDINGS</p>{findings.length?<div className="finding-list">{findings.map((finding,index)=><div key={`${finding}-${index}`}><span>!</span><p>{finding}</p></div>)}</div>:<p className="review-empty">Assignments, family overlaps, school hours, and the supplied school calendar have been reviewed.</p>}</section><section className="source-box"><strong>Source: Maple Grove Elementary 2026–2027 calendar</strong><p>Dates are subject to change. Confirm time-sensitive school details with the school.</p></section><button className="submit">Draft day-of reminders</button><p className="draft-note">Drafts only · 8:00 AM Pacific · Both parents by default · Changes require approval</p></div>
}
function Empty(){return <div className="empty"><span>✦</span><strong>Nothing planned here</strong><p>Add an activity to make it part of the family plan.</p></div>}
