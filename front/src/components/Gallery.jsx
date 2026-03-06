import "../main.css"; 
import React from 'react';


const Gallery = () => {
    return (
        <div className="gallery">
            <h2 className="gallery-title">МЫ В TELEGRAM</h2>
            <p className="gallery-link">@VAMS.msk</p>
            <div className="gallery-image-wrap">
                <img className="gallery-img" src="./src/assets/gallery.png" alt="Gallery" />
            </div>
        </div>

    )
}

export default Gallery
