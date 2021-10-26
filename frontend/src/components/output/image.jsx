import React from "react";
import BaseComponent from "../base_component";
import ComponentExample from "../component_example";

class ImageOutput extends BaseComponent {
  render() {
    return this.props.value ? (
      <div className="output_image">
        <div class="image_preview_holder">
          <img class="image_preview" alt="" src={this.props.value}></img>
        </div>
      </div>
    ) : (
      false
    );
  }
}

class ImageOutputExample extends ComponentExample {
  render() {
    return (
      <img className="output_image_example" src={this.props.value} alt="" />
    );
  }
}

export { ImageOutput, ImageOutputExample };
